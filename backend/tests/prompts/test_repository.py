import pytest

from src.repositories.content_generation import ContentGenerationRepository


@pytest.mark.asyncio
async def test_get_week_context(db_session):
    ctx = await ContentGenerationRepository.get_week_context(
        db=db_session,
        course_id="COURSE_ID",
        week_number=1,
    )

    assert ctx is not None
    assert ctx.week == 1
    assert ctx.course_name
    assert ctx.topics
    assert ctx.learning_outcomes
