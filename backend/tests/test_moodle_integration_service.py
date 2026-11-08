import asyncio

import httpx
import pytest

from src.services.moodle_adapter_exceptions import (
    MoodleEntityNotFoundError,
    MoodleOperationFailedError,
)
from src.services.moodle_client import MoodleClient
from src.services.moodle_error_category import MoodleErrorCategory, normalize_moodle_error
from src.services.moodle_exceptions import (
    MoodleAPIError,
    MoodleAuthenticationError,
    MoodleConnectionError,
    MoodlePermissionError,
    MoodleTimeoutError,
)
from src.services.moodle_integration_service import MoodleIntegrationService
from tests.moodle_fakes import ALL_FUNCTIONS, BASE_URL, TOKEN, FakeMoodle, moodle_exception


def run(coro):
    return asyncio.run(coro)


def make_service(fake: FakeMoodle):
    client = MoodleClient(BASE_URL, TOKEN, transport=httpx.MockTransport(fake.handler))
    return MoodleIntegrationService(client), client


async def with_service(fake: FakeMoodle, operation):
    service, client = make_service(fake)
    try:
        return await operation(service)
    finally:
        await client.aclose()


def test_status_reports_version_and_available_functions():
    fake = FakeMoodle()

    status = run(with_service(fake, lambda service: service.get_status()))

    assert status.connected is True
    assert status.site_name == "Moodle ITK"
    assert status.release.startswith("4.5")
    assert status.version == "2024100701"
    assert [function.name for function in status.functions] == ALL_FUNCTIONS
    assert status.all_functions_available is True


def test_status_marks_missing_functions_unavailable():
    fake = FakeMoodle()
    fake.functions.remove("core_courseformat_update_course")

    status = run(with_service(fake, lambda service: service.get_status()))

    missing = [function.name for function in status.functions if not function.available]
    assert missing == ["core_courseformat_update_course"]
    assert status.all_functions_available is False


def test_list_courses_excludes_the_site_course():
    courses = run(with_service(FakeMoodle(), lambda service: service.list_courses()))

    assert [course.moodle_course_id for course in courses] == [2]
    assert courses[0].fullname == "Pemrograman Web"


def test_get_course_sends_the_id_inside_options():
    fake = FakeMoodle()

    course = run(with_service(fake, lambda service: service.get_course(2)))

    assert course.shortname == "PW101"
    assert fake.called("core_course_get_courses")[0]["options[ids][0]"] == "2"


def test_get_course_raises_not_found_for_unknown_course():
    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(FakeMoodle(), lambda service: service.get_course(999)))


def test_contents_return_what_is_currently_in_moodle_including_page_content():
    contents = run(with_service(FakeMoodle(), lambda service: service.get_course_contents(2)))

    assert [section.name for section in contents.sections] == ["General", "Minggu 1"]
    modules = {module.moodle_module_id: module for module in contents.sections[1].modules}
    assert modules[501].modname == "page"
    assert modules[501].content == "<h2>Isi halaman yang digenerate</h2>"
    assert modules[502].content is None
    assert modules[502].description == "<p>Kerjakan</p>"


def test_contents_still_work_when_page_content_cannot_be_read():
    fake = FakeMoodle()
    fake.failing["mod_page_get_pages_by_courses"] = moodle_exception(
        "accessexception", "Access control exception", "webservice_access_exception"
    )

    contents = run(with_service(fake, lambda service: service.get_course_contents(2)))

    assert contents.sections[1].modules[0].content is None
    assert contents.sections[1].modules[0].name == "Pengantar HTML"


def test_contents_for_unknown_course_raise_not_found_without_reading_contents():
    fake = FakeMoodle()

    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(fake, lambda service: service.get_course_contents(999)))

    assert fake.called("core_course_get_contents") == []


def test_created_course_can_be_read_back():
    fake = FakeMoodle()

    async def scenario(service):
        created = await service.create_course("Basis Data", "BD101", 1)
        listed = await service.list_courses()
        return created, listed

    created, listed = run(with_service(fake, scenario))

    assert created.moodle_course_id == 3
    assert created.fullname == "Basis Data"
    assert created.category_id == 1
    assert [course.shortname for course in listed] == ["PW101", "BD101"]


def test_create_course_with_taken_shortname_raises_api_error():
    with pytest.raises(MoodleAPIError) as info:
        run(with_service(FakeMoodle(), lambda service: service.create_course("Lain", "PW101", 1)))

    assert info.value.code == "shortnametaken"


def test_save_section_creates_a_named_section_that_can_be_read_back():
    fake = FakeMoodle()

    async def scenario(service):
        result = await service.save_section(2, "Minggu 2")
        contents = await service.get_course_contents(2)
        return result, contents

    result, contents = run(with_service(fake, scenario))

    assert result.created is True
    assert result.section.name == "Minggu 2"
    assert result.section.section_number == 2
    assert [section.name for section in contents.sections] == ["General", "Minggu 1", "Minggu 2"]
    rename = fake.called("core_update_inplace_editable")[0]
    assert rename["component"] == "format_topics"
    assert rename["itemtype"] == "sectionname"


def test_save_section_renames_an_existing_section_without_adding_one():
    fake = FakeMoodle()

    result = run(with_service(fake, lambda service: service.save_section(2, "Pendahuluan", 1)))

    assert result.created is False
    assert result.section.moodle_section_id == 202
    assert result.section.name == "Pendahuluan"
    assert fake.called("core_courseformat_update_course") == []


def test_save_section_with_unknown_number_creates_a_new_section():
    fake = FakeMoodle()

    result = run(with_service(fake, lambda service: service.save_section(2, "Minggu 9", 9)))

    assert result.created is True
    assert len(fake.called("core_courseformat_update_course")) == 1


def test_save_section_on_unknown_course_raises_not_found():
    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(FakeMoodle(), lambda service: service.save_section(999, "X")))


def test_invalid_token_surfaces_as_authentication_error_and_never_leaks_the_token():
    fake = FakeMoodle(token="a-different-token")

    with pytest.raises(MoodleAuthenticationError) as info:
        run(with_service(fake, lambda service: service.get_status()))

    assert TOKEN not in str(info.value)


def test_non_list_response_is_rejected_as_invalid_response():
    fake = FakeMoodle()
    fake.failing["core_course_get_courses"] = {"unexpected": "shape"}

    with pytest.raises(MoodleAPIError) as info:
        run(with_service(fake, lambda service: service.list_courses()))

    assert info.value.code == "invalid_response"


def test_error_categories_status_codes_and_retryability():
    cases = [
        (MoodleAuthenticationError("x", code="invalidtoken"), MoodleErrorCategory.AUTHENTICATION, 502, False),
        (MoodlePermissionError("x", code="accessexception"), MoodleErrorCategory.PERMISSION, 502, False),
        (MoodleAPIError("x", code="invalidparameter"), MoodleErrorCategory.VALIDATION, 422, False),
        (MoodleAPIError("x", code="shortnametaken"), MoodleErrorCategory.VALIDATION, 422, False),
        (MoodleTimeoutError("x"), MoodleErrorCategory.TRANSIENT, 504, True),
        (MoodleConnectionError("x"), MoodleErrorCategory.TRANSIENT, 502, True),
        (MoodleAPIError("x", http_status=503, retryable=True), MoodleErrorCategory.TRANSIENT, 502, True),
        (MoodleAPIError("x", code="somethingelse"), MoodleErrorCategory.EXECUTION, 502, False),
    ]

    for error, category, status_code, retryable in cases:
        normalized = normalize_moodle_error(error)
        assert normalized.category == category
        assert normalized.status_code == status_code
        assert normalized.retryable is retryable


def test_adapter_wrapped_errors_are_categorized_by_their_original_error():
    wrapped = MoodleOperationFailedError(
        "gagal", original_error=MoodleAuthenticationError("x", code="invalidtoken")
    )

    normalized = normalize_moodle_error(wrapped)

    assert normalized.category == MoodleErrorCategory.AUTHENTICATION
    assert normalized.moodle_code == "invalidtoken"


def test_adapter_error_without_original_is_an_execution_error():
    normalized = normalize_moodle_error(MoodleOperationFailedError("gagal"))

    assert normalized.category == MoodleErrorCategory.EXECUTION
    assert normalized.moodle_code is None


def test_public_error_message_never_contains_the_moodle_message():
    error = MoodleAPIError(f"detail internal {TOKEN}", code="invalidparameter")

    normalized = normalize_moodle_error(error)

    assert TOKEN not in normalized.message
    assert "detail internal" not in normalized.message


def test_course_can_be_read_by_shortname():
    fake = FakeMoodle()

    course = run(with_service(fake, lambda service: service.get_course_by_shortname("PW101")))

    assert course.moodle_course_id == 2
    assert course.fullname == "Pemrograman Web"
    assert fake.called("core_course_get_courses_by_field")[0]["field"] == "shortname"


def test_unknown_or_site_shortname_is_not_found():
    fake = FakeMoodle()

    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(fake, lambda service: service.get_course_by_shortname("TIDAK-ADA")))
    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(fake, lambda service: service.get_course_by_shortname("ITK")))


def test_course_is_updated_and_read_back():
    fake = FakeMoodle()

    course = run(
        with_service(
            fake,
            lambda service: service.update_course(
                2, fullname="Pemrograman Web Lanjut", summary="<p>Baru</p>", visible=False
            ),
        )
    )

    [sent] = fake.called("core_course_update_courses")
    assert sent["courses[0][id]"] == "2"
    assert "courses[0][shortname]" not in sent
    assert sent["courses[0][summaryformat]"] == "1"
    assert course.fullname == "Pemrograman Web Lanjut"
    assert course.shortname == "PW101"
    assert course.summary == "<p>Baru</p>"
    assert course.visible is False


def test_course_update_warning_is_raised_as_validation_error():
    fake = FakeMoodle()
    run(with_service(fake, lambda service: service.create_course("Basis Data", "BD101", 1)))

    with pytest.raises(MoodleAPIError) as caught:
        run(with_service(fake, lambda service: service.update_course(2, shortname="BD101")))

    assert caught.value.code == "shortnametaken"
    assert normalize_moodle_error(caught.value).category == MoodleErrorCategory.VALIDATION


@pytest.mark.parametrize("changes", [{}, {"fullname": "  "}, {"shortname": ""}])
def test_invalid_course_update_is_rejected_before_calling_moodle(changes):
    fake = FakeMoodle()

    with pytest.raises(ValueError):
        run(with_service(fake, lambda service: service.update_course(2, **changes)))

    assert fake.called("core_course_update_courses") == []


def test_updating_an_unknown_course_is_not_found():
    fake = FakeMoodle()

    with pytest.raises(MoodleEntityNotFoundError):
        run(with_service(fake, lambda service: service.update_course(99, fullname="X")))

    assert fake.called("core_course_update_courses") == []