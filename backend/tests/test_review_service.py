
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError

from src.models.content import ContentStatus
from src.models.activity import ActivityStatus
from src.services.content.review_service import (
    ContentReviewService,
    ActivityReviewService,
    ContentNotFoundError,
    InvalidStatusTransition,
)


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.get = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()

    return db


@pytest.fixture
def content():
    item = MagicMock()
    item.id = "content000000000001"
    item.course_plan_week_id = "week000000000000000001"
    item.status = ContentStatus.DRAFT
    item.content_type = "LEARNING_MATERIAL"
    item.title = "Materi Pengenalan"
    item.content_data = {
        "sections": [{"title": "Pendahuluan", "content": "Materi awal"}],
        "traceability": {"agent_run_id": "old-run"},
    }
    item.content_markdown = "# Materi Pengenalan"
    item.reject_reason = None
    item.reviewer_id = None

    return item


@pytest.fixture
def activity():
    item = MagicMock()
    item.id = "activity00000000001"
    item.course_plan_week_id = "week000000000000000001"
    item.status = ActivityStatus.DRAFT
    item.type = "QUIZ"
    item.title = "Kuis Pengenalan"
    item.activity_data = {
        "questions": [{"question": "Apa itu jaringan komputer?"}]
    }

    return item


@pytest.fixture
def week():
    item = MagicMock()
    item.id = "week000000000000000001"
    item.course_plan_id = "courseplan000000000001"
    item.week_number = 1

    return item


@pytest.fixture
def content_service():
    service = ContentReviewService()
    service.repo = MagicMock()

    service.repo.get_by_id = AsyncMock()
    service.repo.update_status = AsyncMock()
    service.repo.update_content = AsyncMock()

    return service


@pytest.fixture
def activity_service():
    service = ActivityReviewService()
    service.repo = MagicMock()

    service.repo.get_activity_by_id = AsyncMock()
    service.repo.update_activity_status = AsyncMock()
    service.repo.update_activity = AsyncMock()

    return service


# ==========================================
# CONTENT REVIEW
# ==========================================


@pytest.mark.asyncio
async def test_validate_content_success(
    mock_db,
    content,
    content_service,
):
    content_service.repo.get_by_id.return_value = content

    result = await content_service.validate_content(
        mock_db,
        content.id,
    )

    assert result == content
    content_service.repo.update_status.assert_awaited_once_with(
        mock_db,
        content,
        ContentStatus.VALIDATED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_content_not_found(
    mock_db,
    content_service,
):
    content_service.repo.get_by_id.return_value = None

    with pytest.raises(ContentNotFoundError):
        await content_service.validate_content(
            mock_db,
            "invalid-content",
        )

    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_content_invalid_status(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.APPROVED
    content_service.repo.get_by_id.return_value = content

    with pytest.raises(InvalidStatusTransition):
        await content_service.validate_content(
            mock_db,
            content.id,
        )

    content_service.repo.update_status.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_submit_for_review_success(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.VALIDATED
    content_service.repo.get_by_id.return_value = content

    result = await content_service.submit_for_review(
        mock_db,
        content.id,
    )

    assert result == content
    content_service.repo.update_status.assert_awaited_once_with(
        mock_db,
        content,
        ContentStatus.PENDING_REVIEW,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_submit_for_review_invalid_status(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.DRAFT
    content_service.repo.get_by_id.return_value = content

    with pytest.raises(InvalidStatusTransition):
        await content_service.submit_for_review(
            mock_db,
            content.id,
        )

    content_service.repo.update_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_content_success(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.PENDING_REVIEW
    content_service.repo.get_by_id.return_value = content

    result = await content_service.approve_content(
        mock_db,
        content.id,
        reviewer_id="reviewer000000000001",
    )

    assert result == content
    assert content.reviewer_id == "reviewer000000000001"

    content_service.repo.update_status.assert_awaited_once_with(
        mock_db,
        content,
        ContentStatus.APPROVED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_reject_content_success(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.PENDING_REVIEW
    content_service.repo.get_by_id.return_value = content

    result = await content_service.reject_content(
        mock_db,
        content.id,
        reason="Materi perlu diperbaiki.",
        reviewer_id="reviewer000000000001",
    )

    assert result == content
    assert content.reject_reason == "Materi perlu diperbaiki."
    assert content.reviewer_id == "reviewer000000000001"

    content_service.repo.update_status.assert_awaited_once_with(
        mock_db,
        content,
        ContentStatus.REJECTED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_content_success(
    mock_db,
    content,
    week,
    content_service,
):
    content.status = ContentStatus.REJECTED

    content_service.repo.get_by_id.return_value = content
    mock_db.get.return_value = week

    generated_result = MagicMock()
    generated_result.error = None
    generated_result.content_type = "LEARNING_MATERIAL"
    generated_result.material = MagicMock()
    generated_result.ctx = MagicMock()

    generated_row = {
        "title": "Materi Hasil Revisi",
        "content_type": "LEARNING_MATERIAL",
        "content_data": {"sections": []},
        "content_markdown": "# Materi Hasil Revisi",
    }

    with (
        patch(
            "src.services.content.review_service.generate_contents",
            new_callable=AsyncMock,
            return_value=[generated_result],
        ) as mock_generate,
        patch(
            "src.services.content.review_service.to_row",
            return_value=generated_row,
        ),
    ):
        result = await content_service.retry_content(
            mock_db,
            content.id,
            additional_prompt="Tambahkan contoh praktis.",
            revision_notes="Perbaiki penjelasan.",
        )

    assert result == content

    mock_generate.assert_awaited_once()

    generation_kwargs = mock_generate.await_args.kwargs

    assert generation_kwargs["week_numbers"] == [1]
    assert generation_kwargs["content_types"] == ["LEARNING_MATERIAL"]
    assert generation_kwargs["additional_prompt"] == "Tambahkan contoh praktis."
    assert "Catatan penolakan" not in generation_kwargs["revision_notes"]

    content_service.repo.update_content.assert_awaited_once_with(
        mock_db,
        content,
        title="Materi Hasil Revisi",
        content_type="LEARNING_MATERIAL",
        content_data={"sections": []},
        content_markdown="# Materi Hasil Revisi",
    )

    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_content_includes_rejection_reason(
    mock_db,
    content,
    week,
    content_service,
):
    content.status = ContentStatus.REJECTED
    content.reject_reason = "Tambahkan referensi materi."

    content_service.repo.get_by_id.return_value = content
    mock_db.get.return_value = week

    generated_result = MagicMock()
    generated_result.error = None
    generated_result.content_type = "LEARNING_MATERIAL"
    generated_result.material = MagicMock()
    generated_result.ctx = MagicMock()

    with (
        patch(
            "src.services.content.review_service.generate_contents",
            new_callable=AsyncMock,
            return_value=[generated_result],
        ) as mock_generate,
        patch(
            "src.services.content.review_service.to_row",
            return_value={
                "title": "Materi Revisi",
                "content_type": "LEARNING_MATERIAL",
                "content_data": {},
                "content_markdown": "# Materi Revisi",
            },
        ),
    ):
        await content_service.retry_content(
            mock_db,
            content.id,
            revision_notes="Perbaiki bagian referensi.",
        )

    revision_notes = mock_generate.await_args.kwargs["revision_notes"]

    assert "Tambahkan referensi materi." in revision_notes
    assert "Perbaiki bagian referensi." in revision_notes


@pytest.mark.asyncio
async def test_retry_content_generation_failed(
    mock_db,
    content,
    week,
    content_service,
):
    content.status = ContentStatus.DRAFT
    content_service.repo.get_by_id.return_value = content
    mock_db.get.return_value = week

    generated_result = MagicMock()
    generated_result.error = ValueError("Generation failed")

    with patch(
        "src.services.content.review_service.generate_contents",
        new_callable=AsyncMock,
        return_value=[generated_result],
    ):
        with pytest.raises(ValueError, match="Generation failed"):
            await content_service.retry_content(
                mock_db,
                content.id,
            )

    content_service.repo.update_content.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_content_invalid_status(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.APPROVED
    content_service.repo.get_by_id.return_value = content

    with pytest.raises(InvalidStatusTransition):
        await content_service.retry_content(
            mock_db,
            content.id,
        )

    mock_db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_content_week_not_found(
    mock_db,
    content,
    content_service,
):
    content.status = ContentStatus.DRAFT
    content_service.repo.get_by_id.return_value = content
    mock_db.get.return_value = None

    with pytest.raises(ContentNotFoundError):
        await content_service.retry_content(
            mock_db,
            content.id,
        )

    content_service.repo.update_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_content_rollback_on_database_error(
    mock_db,
    content,
    content_service,
):
    content_service.repo.get_by_id.return_value = content
    content_service.repo.update_status.side_effect = SQLAlchemyError(
        "Database error"
    )

    with pytest.raises(SQLAlchemyError):
        await content_service.validate_content(
            mock_db,
            content.id,
        )

    mock_db.rollback.assert_awaited_once()
    mock_db.commit.assert_not_awaited()


# ==========================================
# ACTIVITY REVIEW
# ==========================================


@pytest.mark.asyncio
async def test_validate_activity_success(
    mock_db,
    activity,
    activity_service,
):
    activity_service.repo.get_activity_by_id.return_value = activity

    result = await activity_service.validate_activity(
        mock_db,
        activity.id,
    )

    assert result == activity

    activity_service.repo.update_activity_status.assert_awaited_once_with(
        mock_db,
        activity,
        ActivityStatus.VALIDATED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_activity_not_found(
    mock_db,
    activity_service,
):
    activity_service.repo.get_activity_by_id.return_value = None

    with pytest.raises(ContentNotFoundError):
        await activity_service.validate_activity(
            mock_db,
            "invalid-activity",
        )

    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_activity_invalid_status(
    mock_db,
    activity,
    activity_service,
):
    activity.status = ActivityStatus.EXECUTED
    activity_service.repo.get_activity_by_id.return_value = activity

    with pytest.raises(InvalidStatusTransition):
        await activity_service.validate_activity(
            mock_db,
            activity.id,
        )

    activity_service.repo.update_activity_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_approve_activity_success(
    mock_db,
    activity,
    activity_service,
):
    activity.status = ActivityStatus.VALIDATED
    activity_service.repo.get_activity_by_id.return_value = activity

    result = await activity_service.approve_activity(
        mock_db,
        activity.id,
    )

    assert result == activity

    activity_service.repo.update_activity_status.assert_awaited_once_with(
        mock_db,
        activity,
        ActivityStatus.APPROVED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_mark_activity_executed_success(
    mock_db,
    activity,
    activity_service,
):
    activity.status = ActivityStatus.APPROVED
    activity_service.repo.get_activity_by_id.return_value = activity

    result = await activity_service.mark_executed(
        mock_db,
        activity.id,
    )

    assert result == activity

    activity_service.repo.update_activity_status.assert_awaited_once_with(
        mock_db,
        activity,
        ActivityStatus.EXECUTED,
    )
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_activity_success(
    mock_db,
    activity,
    week,
    activity_service,
):
    activity.status = ActivityStatus.DRAFT
    activity_service.repo.get_activity_by_id.return_value = activity
    mock_db.get.return_value = week

    generated_result = MagicMock()
    generated_result.error = None
    generated_result.content_type = "QUIZ"
    generated_result.material = MagicMock()
    generated_result.ctx = MagicMock()

    generated_row = {
        "title": "Kuis Hasil Revisi",
        "activity_data": {"questions": []},
    }

    with (
        patch(
            "src.services.content.review_service.generate_contents",
            new_callable=AsyncMock,
            return_value=[generated_result],
        ) as mock_generate,
        patch(
            "src.services.content.review_service.to_row",
            return_value=generated_row,
        ),
    ):
        result = await activity_service.retry_activity(
            mock_db,
            activity.id,
            additional_prompt="Buat soal lebih bervariasi.",
        )

    assert result == activity

    generation_kwargs = mock_generate.await_args.kwargs

    assert generation_kwargs["week_numbers"] == [1]
    assert generation_kwargs["content_types"] == ["QUIZ"]
    assert generation_kwargs["additional_prompt"] == "Buat soal lebih bervariasi."

    activity_service.repo.update_activity.assert_awaited_once_with(
        mock_db,
        activity,
        title="Kuis Hasil Revisi",
        activity_data={"questions": []},
    )

    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_retry_activity_generation_failed(
    mock_db,
    activity,
    week,
    activity_service,
):
    activity_service.repo.get_activity_by_id.return_value = activity
    mock_db.get.return_value = week

    generated_result = MagicMock()
    generated_result.error = ValueError("Quiz generation failed")

    with patch(
        "src.services.content.review_service.generate_contents",
        new_callable=AsyncMock,
        return_value=[generated_result],
    ):
        with pytest.raises(ValueError, match="Quiz generation failed"):
            await activity_service.retry_activity(
                mock_db,
                activity.id,
            )

    activity_service.repo.update_activity.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_activity_invalid_status(
    mock_db,
    activity,
    activity_service,
):
    activity.status = ActivityStatus.EXECUTED
    activity_service.repo.get_activity_by_id.return_value = activity

    with pytest.raises(InvalidStatusTransition):
        await activity_service.retry_activity(
            mock_db,
            activity.id,
        )

    mock_db.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_retry_activity_week_not_found(
    mock_db,
    activity,
    activity_service,
):
    activity_service.repo.get_activity_by_id.return_value = activity
    mock_db.get.return_value = None

    with pytest.raises(ContentNotFoundError):
        await activity_service.retry_activity(
            mock_db,
            activity.id,
        )

    activity_service.repo.update_activity.assert_not_awaited()


@pytest.mark.asyncio
async def test_activity_rollback_on_database_error(
    mock_db,
    activity,
    activity_service,
):
    activity_service.repo.get_activity_by_id.return_value = activity
    activity_service.repo.update_activity_status.side_effect = SQLAlchemyError(
        "Database error"
    )

    with pytest.raises(SQLAlchemyError):
        await activity_service.validate_activity(
            mock_db,
            activity.id,
        )

    mock_db.rollback.assert_awaited_once()
    mock_db.commit.assert_not_awaited()
