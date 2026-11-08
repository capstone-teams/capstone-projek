import asyncio
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_assignment_service import (
    ASSIGNMENT_ENTITY_TYPE,
    AssignmentContent,
    AssignmentSettings,
    InvalidAssignmentError,
    MoodleAssignmentService,
    RubricItem,
    assignment_idempotency_key,
    render_assignment_intro,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository

COURSE_ID = 7
SETTING_FIELDS = ("onlinetext", "filesubmission", "maxfiles", "grade", "duedate")


class FakeBridgePlugin:
    """Meniru local_capstonebridge_create_assign / update_assign pada satu course."""

    def __init__(self):
        self.modules = {}
        self.calls = []
        self.fail_with = None
        self._next_cmid = 200

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        function = body.pop("wsfunction")
        for reserved in ("wstoken", "moodlewsrestformat"):
            body.pop(reserved, None)
        self.calls.append((function, body))
        if self.fail_with:
            return httpx.Response(200, json=self.fail_with)
        if function == "local_capstonebridge_create_assign":
            return httpx.Response(200, json=self._create(body))
        if function == "local_capstonebridge_update_assign":
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
        return {
            "cmid": int(body["cmid"]),
            "instanceid": module["instanceid"],
            "section": module["section"],
            "updated": 1,
        }

    @staticmethod
    def _apply(module, body):
        module.update(
            section=int(body["section"]),
            name=body["name"],
            intro=body.get("intro", ""),
            **{name: int(body[name]) for name in SETTING_FIELDS},
        )

    def function_names(self):
        return [function for function, _ in self.calls]


def assignment(**overrides):
    values = {
        "id": "act-001",
        "title": "Normalisasi Studi Kasus Perpustakaan",
        "instructions_markdown": "Normalkan tabel peminjaman buku hingga **3NF**.",
        "expected_outputs": ("Dokumen PDF berisi tahapan normalisasi", "Diagram ERD akhir"),
        "rubric": (
            RubricItem("Ketepatan 1NF-3NF", "Tahapan benar dan lengkap", 60),
            RubricItem("Kualitas ERD", "Relasi dan kardinalitas tepat", 40),
        ),
    }
    values.update(overrides)
    return AssignmentContent(**values)


def run(coro):
    return asyncio.run(coro)


def publish_all(plugin, mappings, *steps):
    async def scenario():
        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
        try:
            service = MoodleAssignmentService(client, mappings)
            return [await service.publish(COURSE_ID, *step) for step in steps]
        finally:
            await client.aclose()

    return run(scenario())


def test_first_publish_creates_the_assignment_in_the_week_section_with_default_settings():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (3, assignment()))

    module = plugin.modules[result.cmid]
    assert result.created is True
    assert result.idempotency_key == "capstone-assignment-act-001"
    assert module["idnumber"] == result.idempotency_key
    assert module["section"] == 3
    assert module["name"] == "Normalisasi Studi Kasus Perpustakaan"
    assert module["onlinetext"] == 1
    assert module["filesubmission"] == 1
    assert module["maxfiles"] == 5
    assert module["grade"] == 100
    assert module["duedate"] == 0
    assert plugin.function_names() == ["local_capstonebridge_create_assign"]
    assert run(mappings.get_moodle_id(ASSIGNMENT_ENTITY_TYPE, "act-001")) == result.cmid


def test_republishing_updates_the_same_activity_without_duplicates():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(plugin, mappings, (3, assignment()), (3, assignment()))

    assert second.created is False
    assert second.cmid == first.cmid
    assert len(plugin.modules) == 1
    assert plugin.function_names() == [
        "local_capstonebridge_create_assign",
        "local_capstonebridge_update_assign",
    ]


def test_changed_assignment_and_settings_are_applied_to_the_same_activity():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    due = datetime(2026, 12, 1, 23, 59, tzinfo=timezone(timedelta(hours=8)))
    settings = AssignmentSettings(submission_types=("file",), max_files=2, max_grade=80, due=due)

    first, second = publish_all(
        plugin,
        mappings,
        (3, assignment()),
        (4, assignment(title="Normalisasi (revisi)"), settings),
    )

    module = plugin.modules[first.cmid]
    assert second.cmid == first.cmid
    assert module["section"] == 4
    assert module["name"] == "Normalisasi (revisi)"
    assert module["onlinetext"] == 0
    assert module["filesubmission"] == 1
    assert module["maxfiles"] == 2
    assert module["grade"] == 80
    assert module["duedate"] == int(due.timestamp())
    assert len(plugin.modules) == 1


def test_activity_left_in_moodle_without_mapping_is_reused_and_mapped():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    publish_all(plugin, InMemoryMoodleMappingRepository(), (3, assignment()))  # mapping hilang
    plugin.calls.clear()

    [result] = publish_all(plugin, mappings, (5, assignment(title="Judul baru")))

    assert result.created is False
    assert len(plugin.modules) == 1
    assert plugin.modules[result.cmid]["section"] == 5
    assert plugin.modules[result.cmid]["name"] == "Judul baru"
    assert plugin.function_names() == [
        "local_capstonebridge_create_assign",
        "local_capstonebridge_update_assign",
    ]
    assert run(mappings.get_moodle_id(ASSIGNMENT_ENTITY_TYPE, "act-001")) == result.cmid


def test_different_assignments_get_different_activities():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(plugin, mappings, (1, assignment()), (1, assignment(id="act-002")))

    assert first.cmid != second.cmid
    assert len(plugin.modules) == 2


def test_intro_contains_instructions_expected_outputs_and_rubric():
    intro = render_assignment_intro(assignment())

    assert intro.startswith("<p>Normalkan tabel peminjaman buku hingga <strong>3NF</strong>.</p>")
    assert "<h5>Hasil yang Dikumpulkan</h5>" in intro
    assert "<li>Diagram ERD akhir</li>" in intro
    assert "<h5>Kriteria Penilaian</h5>" in intro
    assert "<td>Ketepatan 1NF-3NF</td><td>Tahapan benar dan lengkap</td><td>60%</td>" in intro
    assert "<td>Kualitas ERD</td><td>Relasi dan kardinalitas tepat</td><td>40%</td>" in intro


def test_instructions_markdown_is_converted_and_raw_html_is_escaped():
    intro = render_assignment_intro(
        assignment(
            instructions_markdown=(
                "## Langkah\n\n1. Identifikasi entity\n2. Buat `ERD`\n\n"
                "- poin *penting*\n- <script>alert(1)</script>\n\nBaris satu\nbaris dua"
            ),
            expected_outputs=(),
            rubric=(),
        )
    )

    assert intro == (
        "<h5>Langkah</h5>"
        "<ol><li>Identifikasi entity</li><li>Buat <code>ERD</code></li></ol>"
        "<ul><li>poin <em>penting</em></li><li>&lt;script&gt;alert(1)&lt;/script&gt;</li></ul>"
        "<p>Baris satu<br>baris dua</p>"
    )


@pytest.mark.parametrize(
    ("week", "content", "settings"),
    [
        (-1, {}, {}),
        (1, {"id": ""}, {}),
        (1, {"id": "x" * 100}, {}),
        (1, {"title": "  "}, {}),
        (1, {"title": "x" * 256}, {}),
        (1, {"instructions_markdown": " "}, {}),
        (1, {"rubric": (RubricItem("A", "a", 50), RubricItem("B", "b", 30))}, {}),
        (1, {"rubric": (RubricItem(" ", "a", 100),)}, {}),
        (1, {}, {"submission_types": ()}),
        (1, {}, {"submission_types": ("onlinetext",)}),
        (1, {}, {"max_files": 0}),
        (1, {}, {"max_files": 21}),
        (1, {}, {"max_grade": 0}),
        (1, {}, {"due": datetime(2026, 12, 1, 23, 59)}),
    ],
)
def test_invalid_assignment_is_rejected_before_calling_moodle(week, content, settings):
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    with pytest.raises(InvalidAssignmentError):
        publish_all(plugin, mappings, (week, assignment(**content), AssignmentSettings(**settings)))

    assert plugin.calls == []


def test_moodle_error_is_raised_and_no_mapping_is_saved():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    plugin.fail_with = {
        "exception": "invalid_parameter_exception",
        "errorcode": "invalidparameter",
        "message": "Invalid parameter value detected",
    }

    with pytest.raises(MoodleAPIError):
        publish_all(plugin, mappings, (1, assignment()))

    assert run(mappings.exists(ASSIGNMENT_ENTITY_TYPE, "act-001")) is False


def test_assignment_is_built_from_activity_data():
    activity_data = {
        "instructions_markdown": "Normalkan tabel peminjaman buku hingga **3NF**.",
        "expected_outputs": ["Dokumen PDF berisi tahapan normalisasi", "Diagram ERD akhir"],
        "rubric": [
            {"criterion": "Ketepatan 1NF-3NF", "description": "Tahapan benar dan lengkap", "weight_percent": 60},
            {"criterion": "Kualitas ERD", "description": "Relasi dan kardinalitas tepat", "weight_percent": 40},
        ],
        "traceability": {
            "week_number": 3,
            "sub_cpmk_codes": ["Sub-CPMK-3.1"],
            "weekly_plan_ref": "week-3",
        },
    }

    built = AssignmentContent.from_activity("act-001", "Normalisasi Studi Kasus Perpustakaan", activity_data)

    assert built == assignment()


def test_invalid_activity_data_is_rejected():
    with pytest.raises(InvalidAssignmentError):
        AssignmentContent.from_activity("act-001", "Tugas", {"instructions_markdown": "Kerjakan"})


def test_idempotency_key_is_stable():
    assert assignment_idempotency_key("act-001") == assignment_idempotency_key("act-001")
    assert assignment_idempotency_key("act-001") != assignment_idempotency_key("act-002")


def test_result_can_be_serialized():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (3, assignment()))

    assert result.to_dict() == {
        "assignment_id": "act-001",
        "moodle_course_id": COURSE_ID,
        "week": 3,
        "cmid": result.cmid,
        "instance_id": result.instance_id,
        "idempotency_key": "capstone-assignment-act-001",
        "created": True,
        "submission_types": ["online_text", "file"],
        "max_files": 5,
        "max_grade": 100,
        "due": None,
    }


@pytest.mark.asyncio
async def test_moodle_object_id_is_stored_in_the_mapping_table(db_session):
    plugin = FakeBridgePlugin()
    repository = SqlMoodleMappingRepository(db_session)
    client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
    try:
        service = MoodleAssignmentService(client, repository)
        first = await service.publish(COURSE_ID, 3, assignment())
        second = await service.publish(COURSE_ID, 3, assignment())
    finally:
        await client.aclose()

    rows = (
        await db_session.execute(
            select(MoodleEntityMapping).where(MoodleEntityMapping.entity_type == ASSIGNMENT_ENTITY_TYPE)
        )
    ).scalars().all()
    assert [(row.internal_id, row.moodle_id) for row in rows] == [("act-001", first.cmid)]
    assert second.cmid == first.cmid