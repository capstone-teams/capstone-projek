import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_html import markdown_to_html, paragraphs_html
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_page_service import (
    PAGE_ENTITY_TYPE,
    InvalidLearningMaterialError,
    LearningMaterialPage,
    MoodlePageService,
    page_idempotency_key,
)

COURSE_ID = 7


class FakeBridgePlugin:
    """Meniru local_capstonebridge_create_page / update_page pada satu course."""

    def __init__(self):
        self.modules = {}
        self.calls = []
        self.fail_with = None
        self._next_cmid = 400

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode(), keep_blank_values=True).items()}
        function = body.pop("wsfunction")
        for reserved in ("wstoken", "moodlewsrestformat"):
            body.pop(reserved, None)
        self.calls.append((function, body))
        if self.fail_with:
            return httpx.Response(200, json=self.fail_with)
        if function == "local_capstonebridge_create_page":
            return httpx.Response(200, json=self._create(body))
        if function == "local_capstonebridge_update_page":
            return httpx.Response(200, json=self._update(body))
        raise AssertionError(f"function tidak terduga: {function}")

    def _create(self, body):
        for cmid, module in self.modules.items():
            if body.get("idnumber") and module["idnumber"] == body["idnumber"]:
                return {"cmid": cmid, "instanceid": module["instanceid"], "created": 0}
        cmid = self._next_cmid
        self._next_cmid += 1
        self.modules[cmid] = {"instanceid": cmid + 1000, "idnumber": body.get("idnumber", "")}
        self._apply(self.modules[cmid], body)
        return {"cmid": cmid, "instanceid": cmid + 1000, "created": 1}

    def _update(self, body):
        module = self.modules[int(body["cmid"])]
        self._apply(module, body)
        return {"cmid": int(body["cmid"]), "instanceid": module["instanceid"], "section": module["section"],
                "updated": 1}

    @staticmethod
    def _apply(module, body):
        module.update(section=int(body["section"]), name=body["name"], content=body["content"],
                      intro=body.get("intro", ""))

    def function_names(self):
        return [function for function, _ in self.calls]


def page(**overrides):
    values = {
        "id": "content-001",
        "title": "Pengantar Basis Data",
        "content_html": "<h2>Apa itu basis data?</h2><p>Kumpulan data terstruktur.</p>",
    }
    values.update(overrides)
    return LearningMaterialPage(**values)


def run(coro):
    return asyncio.run(coro)


def publish_all(plugin, mappings, *steps):
    async def scenario():
        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
        try:
            service = MoodlePageService(client, mappings)
            return [await service.publish(COURSE_ID, week, item) for week, item in steps]
        finally:
            await client.aclose()

    return run(scenario())


def test_first_publish_creates_the_page_in_the_week_section():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (1, page()))

    module = plugin.modules[result.cmid]
    assert result.created is True
    assert result.idempotency_key == "capstone-page-content-001"
    assert module["idnumber"] == result.idempotency_key
    assert module["section"] == 1
    assert module["name"] == "Pengantar Basis Data"
    assert module["content"] == "<h2>Apa itu basis data?</h2><p>Kumpulan data terstruktur.</p>"
    assert plugin.function_names() == ["local_capstonebridge_create_page"]
    assert run(mappings.get_moodle_id(PAGE_ENTITY_TYPE, "content-001")) == result.cmid


def test_republishing_updates_the_same_page_without_duplicates():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(plugin, mappings, (1, page()), (1, page()))

    assert second.created is False
    assert second.cmid == first.cmid
    assert len(plugin.modules) == 1
    assert plugin.function_names() == [
        "local_capstonebridge_create_page",
        "local_capstonebridge_update_page",
    ]


def test_changed_page_is_updated_and_moved_to_the_new_week():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    changed = page(title="Pengantar Basis Data (revisi)", content_html="<p>Versi 2</p>", summary="Ringkas")

    first, second = publish_all(plugin, mappings, (1, page()), (2, changed))

    module = plugin.modules[first.cmid]
    assert second.cmid == first.cmid
    assert module["section"] == 2
    assert module["name"] == "Pengantar Basis Data (revisi)"
    assert module["content"] == "<p>Versi 2</p>"
    assert module["intro"] == "<p>Ringkas</p>"
    assert len(plugin.modules) == 1


def test_page_left_in_moodle_without_mapping_is_reused_and_mapped():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    publish_all(plugin, InMemoryMoodleMappingRepository(), (1, page()))  # mapping hilang
    plugin.calls.clear()

    [result] = publish_all(plugin, mappings, (3, page(title="Judul baru")))

    assert result.created is False
    assert len(plugin.modules) == 1
    assert plugin.modules[result.cmid]["section"] == 3
    assert plugin.function_names() == [
        "local_capstonebridge_create_page",
        "local_capstonebridge_update_page",
    ]
    assert run(mappings.get_moodle_id(PAGE_ENTITY_TYPE, "content-001")) == result.cmid


@pytest.mark.parametrize(
    ("week", "overrides"),
    [
        (-1, {}),
        (1, {"id": ""}),
        (1, {"id": "x" * 100}),
        (1, {"title": "  "}),
        (1, {"title": "x" * 256}),
        (1, {"content_html": "   "}),
    ],
)
def test_invalid_page_is_rejected_before_calling_moodle(week, overrides):
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    with pytest.raises(InvalidLearningMaterialError):
        publish_all(plugin, mappings, (week, page(**overrides)))

    assert plugin.calls == []


def test_moodle_error_is_raised_and_no_mapping_is_saved():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    plugin.fail_with = {
        "exception": "invalid_parameter_exception",
        "errorcode": "invalidparameter",
        "message": "Invalid parameter value detected",
    }

    with pytest.raises(MoodleAPIError):
        publish_all(plugin, mappings, (1, page()))

    assert run(mappings.exists(PAGE_ENTITY_TYPE, "content-001")) is False


def test_page_is_built_from_learning_material_data():
    content_data = {
        "learning_objectives": ["Menjelaskan konsep basis data"],
        "sections": [
            {"heading": "Pengantar", "body_markdown": "Basis data menyimpan **data terstruktur**."},
            {"heading": "Contoh <SQL>", "body_markdown": "```\nSELECT * FROM mahasiswa;\n```"},
        ],
        "references": [
            {"title": "Dokumentasi PostgreSQL", "url": "https://www.postgresql.org/docs/"},
            {"title": "Buku ajar Basis Data", "url": None},
        ],
        "traceability": {
            "week_number": 1,
            "sub_cpmk_codes": ["Sub-CPMK-1.1"],
            "weekly_plan_ref": "week-1",
        },
    }

    built = LearningMaterialPage.from_content("content-001", "Pengantar Basis Data", content_data)

    assert built.id == "content-001"
    assert built.content_html == (
        "<h3>Tujuan Pembelajaran</h3><ul><li>Menjelaskan konsep basis data</li></ul>"
        "<h3>Pengantar</h3><p>Basis data menyimpan <strong>data terstruktur</strong>.</p>"
        "<h3>Contoh &lt;SQL&gt;</h3><pre><code>SELECT * FROM mahasiswa;</code></pre>"
        '<h3>Referensi</h3><ul><li><a href="https://www.postgresql.org/docs/">Dokumentasi PostgreSQL</a></li>'
        "<li>Buku ajar Basis Data</li></ul>"
    )


def test_invalid_learning_material_data_is_rejected():
    with pytest.raises(InvalidLearningMaterialError):
        LearningMaterialPage.from_content("content-001", "Materi", {"sections": []})


def test_markdown_is_converted_and_raw_html_is_escaped():
    assert markdown_to_html("# Judul\n\n<script>alert(1)</script>\n\n1. satu\n2. *dua*") == (
        "<h2>Judul</h2><p>&lt;script&gt;alert(1)&lt;/script&gt;</p><ol><li>satu</li><li><em>dua</em></li></ol>"
    )
    assert markdown_to_html("## A", heading_tag="h5") == "<h5>A</h5>"
    assert markdown_to_html("```\n<b>x</b>") == "<pre><code>&lt;b&gt;x&lt;/b&gt;</code></pre>"
    assert paragraphs_html("A & B\n\nC") == "<p>A &amp; B</p><p>C</p>"


def test_idempotency_key_is_stable():
    assert page_idempotency_key("c-1") == page_idempotency_key("c-1")
    assert page_idempotency_key("c-1") != page_idempotency_key("c-2")


def test_result_can_be_serialized():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (1, page()))

    assert result.to_dict() == {
        "content_id": "content-001",
        "moodle_course_id": COURSE_ID,
        "week": 1,
        "cmid": result.cmid,
        "instance_id": result.instance_id,
        "idempotency_key": "capstone-page-content-001",
        "created": True,
    }


@pytest.mark.asyncio
async def test_moodle_object_id_is_stored_in_the_mapping_table(db_session):
    plugin = FakeBridgePlugin()
    repository = SqlMoodleMappingRepository(db_session)
    client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
    try:
        service = MoodlePageService(client, repository)
        first = await service.publish(COURSE_ID, 1, page())
        second = await service.publish(COURSE_ID, 1, page())
    finally:
        await client.aclose()

    rows = (
        await db_session.execute(
            select(MoodleEntityMapping).where(MoodleEntityMapping.entity_type == PAGE_ENTITY_TYPE)
        )
    ).scalars().all()
    assert [(row.internal_id, row.moodle_id) for row in rows] == [("content-001", first.cmid)]
    assert second.cmid == first.cmid