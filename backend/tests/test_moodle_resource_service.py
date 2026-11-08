import asyncio
from urllib.parse import parse_qs

import httpx
import pytest
from sqlalchemy import select

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleAPIError
from src.services.moodle_mapping import InMemoryMoodleMappingRepository
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository
from src.services.moodle_resource_service import (
    RESOURCE_ENTITY_TYPE,
    InvalidLearningResourceError,
    LearningResource,
    MoodleResourceService,
    resource_idempotency_key,
)

COURSE_ID = 7


class FakeBridgePlugin:
    """Meniru local_capstonebridge_create_url / update_url pada satu course."""

    def __init__(self):
        self.modules = {}
        self.calls = []
        self.fail_with = None
        self._next_cmid = 100

    def handler(self, request):
        body = {key: values[0] for key, values in parse_qs(request.content.decode()).items()}
        function = body.pop("wsfunction")
        for reserved in ("wstoken", "moodlewsrestformat"):
            body.pop(reserved, None)
        self.calls.append((function, body))
        if self.fail_with:
            return httpx.Response(200, json=self.fail_with)
        if function == "local_capstonebridge_create_url":
            return httpx.Response(200, json=self._create(body))
        if function == "local_capstonebridge_update_url":
            return httpx.Response(200, json=self._update(body))
        raise AssertionError(f"function tidak terduga: {function}")

    def _create(self, body):
        for cmid, module in self.modules.items():
            if body.get("idnumber") and module["idnumber"] == body["idnumber"]:
                return {"cmid": cmid, "instanceid": module["instanceid"], "created": 0}
        cmid = self._next_cmid
        self._next_cmid += 1
        self.modules[cmid] = {
            "instanceid": cmid + 1000,
            "idnumber": body.get("idnumber", ""),
            "section": int(body["section"]),
            "name": body["name"],
            "url": body["externalurl"],
            "intro": body.get("intro", ""),
        }
        return {"cmid": cmid, "instanceid": cmid + 1000, "created": 1}

    def _update(self, body):
        module = self.modules[int(body["cmid"])]
        module.update(
            name=body["name"],
            url=body["externalurl"],
            intro=body.get("intro", ""),
            section=int(body["section"]),
        )
        return {
            "cmid": int(body["cmid"]),
            "instanceid": module["instanceid"],
            "section": module["section"],
            "updated": 1,
        }

    def function_names(self):
        return [function for function, _ in self.calls]


def resource(**overrides):
    values = {
        "id": "res-001",
        "title": "Dokumentasi PostgreSQL",
        "url": "https://www.postgresql.org/docs/",
        "description": "Bacaan pendukung minggu 2",
    }
    values.update(overrides)
    return LearningResource(**values)


def run(coro):
    return asyncio.run(coro)


def publish_all(plugin, mappings, *steps):
    async def scenario():
        client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
        try:
            service = MoodleResourceService(client, mappings)
            return [await service.publish(COURSE_ID, week, item) for week, item in steps]
        finally:
            await client.aclose()

    return run(scenario())


def test_first_publish_creates_the_resource_in_the_week_section():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (2, resource()))

    module = plugin.modules[result.cmid]
    assert result.created is True
    assert result.week == 2
    assert result.idempotency_key == "capstone-resource-res-001"
    assert module["section"] == 2
    assert module["url"] == "https://www.postgresql.org/docs/"
    assert module["idnumber"] == result.idempotency_key
    assert plugin.function_names() == ["local_capstonebridge_create_url"]
    assert run(mappings.get_moodle_id(RESOURCE_ENTITY_TYPE, "res-001")) == result.cmid


def test_republishing_updates_the_same_activity_without_duplicates():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(plugin, mappings, (2, resource()), (2, resource()))

    assert second.created is False
    assert second.cmid == first.cmid
    assert len(plugin.modules) == 1
    assert plugin.function_names() == [
        "local_capstonebridge_create_url",
        "local_capstonebridge_update_url",
    ]


def test_changed_resource_is_updated_and_moved_to_the_new_week():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    changed = resource(title="Dokumentasi PostgreSQL 17", url="https://www.postgresql.org/docs/17/")

    first, second = publish_all(plugin, mappings, (2, resource()), (5, changed))

    module = plugin.modules[first.cmid]
    assert second.cmid == first.cmid
    assert module["section"] == 5
    assert module["name"] == "Dokumentasi PostgreSQL 17"
    assert module["url"] == "https://www.postgresql.org/docs/17/"
    assert len(plugin.modules) == 1


def test_activity_left_in_moodle_without_mapping_is_reused_and_mapped():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    publish_all(plugin, InMemoryMoodleMappingRepository(), (2, resource()))  # mapping hilang
    plugin.calls.clear()

    [result] = publish_all(plugin, mappings, (3, resource(title="Judul baru")))

    assert result.created is False
    assert len(plugin.modules) == 1
    assert plugin.modules[result.cmid]["section"] == 3
    assert plugin.modules[result.cmid]["name"] == "Judul baru"
    assert plugin.function_names() == [
        "local_capstonebridge_create_url",
        "local_capstonebridge_update_url",
    ]
    assert run(mappings.get_moodle_id(RESOURCE_ENTITY_TYPE, "res-001")) == result.cmid


def test_different_resources_get_different_activities():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    first, second = publish_all(
        plugin, mappings, (1, resource()), (1, resource(id="res-002", url="https://sqlbolt.com/"))
    )

    assert first.cmid != second.cmid
    assert len(plugin.modules) == 2


def test_description_is_sent_as_escaped_html_paragraphs():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(
        plugin, mappings, (1, resource(description="Baca bab 1 & 2.\n\n<b>Wajib</b> sebelum kuis."))
    )

    assert plugin.modules[result.cmid]["intro"] == (
        "<p>Baca bab 1 &amp; 2.</p><p>&lt;b&gt;Wajib&lt;/b&gt; sebelum kuis.</p>"
    )


@pytest.mark.parametrize(
    ("week", "overrides"),
    [
        (1, {"url": "ftp://example.com/file"}),
        (1, {"url": "example.com/tanpa-skema"}),
        (1, {"url": ""}),
        (1, {"title": "   "}),
        (1, {"id": ""}),
        (1, {"id": "x" * 100}),
        (1, {"resource_type": "file"}),
        (-1, {}),
    ],
)
def test_invalid_resource_is_rejected_before_calling_moodle(week, overrides):
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    with pytest.raises(InvalidLearningResourceError):
        publish_all(plugin, mappings, (week, resource(**overrides)))

    assert plugin.calls == []


def test_moodle_error_is_raised_and_no_mapping_is_saved():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()
    plugin.fail_with = {
        "exception": "invalid_parameter_exception",
        "errorcode": "invalidparameter",
        "message": "Invalid parameter value detected",
    }

    with pytest.raises(MoodleAPIError):
        publish_all(plugin, mappings, (1, resource()))

    assert run(mappings.exists(RESOURCE_ENTITY_TYPE, "res-001")) is False


def test_resource_is_built_from_a_content_schema_item():
    item = LearningResource.from_content(
        {
            "id": "res-010",
            "type": "resource",
            "title": "Database Reference",
            "description": "Referensi utama",
            "resource_type": "external_link",
            "url": "https://example.com",
        }
    )

    assert item == LearningResource(
        id="res-010",
        title="Database Reference",
        url="https://example.com",
        description="Referensi utama",
        resource_type="external_link",
    )


def test_content_item_of_another_type_is_rejected():
    with pytest.raises(InvalidLearningResourceError):
        LearningResource.from_content({"id": "x", "type": "learning_material", "title": "Bab 1"})


def test_idempotency_key_is_stable():
    assert resource_idempotency_key("res-001") == resource_idempotency_key("res-001")
    assert resource_idempotency_key("res-001") != resource_idempotency_key("res-002")


def test_result_can_be_serialized():
    plugin, mappings = FakeBridgePlugin(), InMemoryMoodleMappingRepository()

    [result] = publish_all(plugin, mappings, (2, resource()))

    assert result.to_dict() == {
        "resource_id": "res-001",
        "moodle_course_id": COURSE_ID,
        "week": 2,
        "cmid": result.cmid,
        "instance_id": result.instance_id,
        "idempotency_key": "capstone-resource-res-001",
        "created": True,
    }


@pytest.mark.asyncio
async def test_moodle_object_id_is_stored_in_the_mapping_table(db_session):
    plugin = FakeBridgePlugin()
    repository = SqlMoodleMappingRepository(db_session)
    client = MoodleClient("http://moodle.test", "token", transport=httpx.MockTransport(plugin.handler))
    try:
        service = MoodleResourceService(client, repository)
        first = await service.publish(COURSE_ID, 2, resource())
        second = await service.publish(COURSE_ID, 2, resource())
    finally:
        await client.aclose()

    rows = (
        await db_session.execute(
            select(MoodleEntityMapping).where(MoodleEntityMapping.entity_type == RESOURCE_ENTITY_TYPE)
        )
    ).scalars().all()
    assert [(row.internal_id, row.moodle_id) for row in rows] == [("res-001", first.cmid)]
    assert second.cmid == first.cmid