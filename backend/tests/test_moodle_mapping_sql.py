import httpx
import pytest
from sqlalchemy import func, select

from src.models.moodle_entity_mapping import MoodleEntityMapping
from src.services.moodle_adapter import MoodleAdapter
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import DuplicateMappingError, MoodleMapping
from src.services.moodle_mapping_sql import SqlMoodleMappingRepository


async def count_rows(session) -> int:
    return (await session.execute(select(func.count()).select_from(MoodleEntityMapping))).scalar_one()


@pytest.mark.asyncio
async def test_save_and_lookup_in_both_directions(db_session):
    repo = SqlMoodleMappingRepository(db_session)

    await repo.save(MoodleMapping("course", "course_1", 42))

    assert await repo.get_moodle_id("course", "course_1") == 42
    assert await repo.get_internal_id("course", 42) == "course_1"
    assert await repo.exists("course", "course_1") is True


@pytest.mark.asyncio
async def test_unknown_entity_has_no_mapping(db_session):
    repo = SqlMoodleMappingRepository(db_session)

    assert await repo.get_moodle_id("course", "belum-ada") is None
    assert await repo.get_internal_id("course", 999) is None
    assert await repo.exists("course", "belum-ada") is False


@pytest.mark.asyncio
async def test_saving_the_same_mapping_twice_keeps_one_row(db_session):
    repo = SqlMoodleMappingRepository(db_session)

    await repo.save(MoodleMapping("activity", "activity_123", 456))
    await repo.save(MoodleMapping("activity", "activity_123", 456))

    assert await count_rows(db_session) == 1


@pytest.mark.asyncio
async def test_remapping_internal_id_to_another_moodle_id_is_rejected(db_session):
    repo = SqlMoodleMappingRepository(db_session)
    await repo.save(MoodleMapping("course", "course_1", 42))

    with pytest.raises(DuplicateMappingError):
        await repo.save(MoodleMapping("course", "course_1", 43))

    assert await repo.get_moodle_id("course", "course_1") == 42


@pytest.mark.asyncio
async def test_same_moodle_id_for_another_internal_id_is_rejected_by_database(db_session):
    repo = SqlMoodleMappingRepository(db_session)
    await repo.save(MoodleMapping("course", "course_1", 42))

    with pytest.raises(DuplicateMappingError):
        await repo.save(MoodleMapping("course", "course_2", 42))

    assert await count_rows(db_session) == 1
    # Session tetap bisa dipakai setelah rollback.
    await repo.save(MoodleMapping("course", "course_3", 43))
    assert await count_rows(db_session) == 2


@pytest.mark.asyncio
async def test_same_internal_id_is_allowed_for_different_entity_types(db_session):
    repo = SqlMoodleMappingRepository(db_session)

    await repo.save(MoodleMapping("course", "item_1", 10))
    await repo.save(MoodleMapping("section", "item_1", 10))

    assert await repo.get_moodle_id("course", "item_1") == 10
    assert await repo.get_moodle_id("section", "item_1") == 10


@pytest.mark.asyncio
async def test_retry_after_restart_does_not_create_a_second_moodle_course(db_session):
    """Adapter baru (mis. setelah server restart) harus mengenali course yang sudah dibuat."""
    created = {"count": 0}

    def handler(request):
        body = request.content.decode()
        if "wsfunction=core_course_create_courses" in body:
            created["count"] += 1
            return httpx.Response(200, json=[{"id": 77, "shortname": "cs101"}])
        return httpx.Response(200, json=[{"id": 77, "fullname": "CS 101", "shortname": "cs101"}])

    def new_adapter():
        client = MoodleClient("http://moodle.test", "test-token", transport=httpx.MockTransport(handler))
        return MoodleAdapter(client, SqlMoodleMappingRepository(db_session)), client

    first, first_client = new_adapter()
    await first.create_course("course_1", "CS 101", "cs101")
    await first_client.aclose()

    second, second_client = new_adapter()
    dto = await second.create_course("course_1", "CS 101", "cs101")
    await second_client.aclose()

    assert dto.moodle_id == 77
    assert created["count"] == 1
    assert await count_rows(db_session) == 1