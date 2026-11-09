import pytest

from unittest.mock import MagicMock, AsyncMock, patch

from src.services.content.generate_service import (
    generate_contents,
    ContentGenerationError,
)

@pytest.fixture
def mock_db():
    db = MagicMock()

    plan = MagicMock()
    plan.id = "courseplan000000000001"

    week_1 = MagicMock()
    week_1.id = "week000000000000000001"
    week_1.week_number = 1
    week_1.week_type = "regular"
    week_1.title = "Pengenalan Materi"
    week_1.learning_outcomes = ["Memahami konsep dasar"]
    week_1.topics = ["Konsep dasar"]
    week_1.methods = ["Ceramah"]
    week_1.assessment = "Tugas"
    week_1.metadata_ = {}

    week_2 = MagicMock()
    week_2.id = "week000000000000000002"
    week_2.week_number = 2
    week_2.week_type = "regular"
    week_2.title = "Pendalaman Materi"
    week_2.learning_outcomes = ["Memahami materi lanjutan"]
    week_2.topics = ["Materi lanjutan"]
    week_2.methods = ["Diskusi"]
    week_2.assessment = "Kuis"
    week_2.metadata_ = {}

    week_3 = MagicMock()
    week_3.id = "week000000000000000003"
    week_3.week_number = 3
    week_3.week_type = "regular"
    week_3.title = "Penerapan Materi"
    week_3.learning_outcomes = [
        "Menerapkan konsep yang telah dipelajari"
    ]
    week_3.topics = ["Penerapan konsep dasar"]
    week_3.methods = ["Praktik"]
    week_3.assessment = "Tugas"
    week_3.metadata_ = {}

    week_kuis = MagicMock()
    week_kuis.id = "week000000000000000004"
    week_kuis.week_number = 4
    week_kuis.week_type = "kuis"
    week_kuis.title = "Evaluasi Materi"
    week_kuis.learning_outcomes = [
        "Mengevaluasi pemahaman materi"
    ]
    week_kuis.topics = ["Materi minggu 1 sampai 3"]
    week_kuis.methods = ["Evaluasi"]
    week_kuis.assessment = "Kuis"
    week_kuis.metadata_ = {}

    week_uts = MagicMock()
    week_uts.id = "week000000000000000008"
    week_uts.week_number = 8
    week_uts.week_type = "uts"
    week_uts.title = "Ujian Tengah Semester"
    week_uts.learning_outcomes = []
    week_uts.topics = []
    week_uts.methods = []
    week_uts.assessment = "UTS"
    week_uts.metadata_ = {}

    week_uas = MagicMock()
    week_uas.id = "week000000000000000016"
    week_uas.week_number = 16
    week_uas.week_type = "uas"
    week_uas.title = "Ujian Akhir Semester"
    week_uas.learning_outcomes = []
    week_uas.topics = []
    week_uas.methods = []
    week_uas.assessment = "UAS"
    week_uas.metadata_ = {}

    result = MagicMock()
    result.all.return_value = [
        (plan, week_1),
        (plan, week_2),
        (plan, week_3),
        (plan, week_kuis),
        (plan, week_uts),
        (plan, week_uas),
    ]

    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()

    db.plan = plan
    db.week_1 = week_1
    db.week_2 = week_2
    db.week_3 = week_3
    db.week_kuis = week_kuis
    db.week_uts = week_uts
    db.week_uas = week_uas

    return db

@pytest.fixture
def mock_repository():
    repository = AsyncMock()
    repository.get_context = AsyncMock()
    return repository


@pytest.fixture
def mock_llm():
    return AsyncMock()


@pytest.mark.asyncio
async def test_generate_contents_returns_results(mock_db):
    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[1],
        concurrency=1,
    )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_generate_quiz_when_week_type_is_kuis(mock_db):
    result = MagicMock()
    result.all.return_value = [
        (mock_db.plan, mock_db.week_kuis)
    ]
    mock_db.execute = AsyncMock(return_value=result)

    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[4],
        concurrency=1,
        include_resources=False,
    )

    assert len(results) == 1
    assert results[0].content_type == "QUIZ"
    assert results[0].ctx.week == 4
    assert results[0].ctx.week_data.week_type == "kuis"

@pytest.mark.asyncio
async def test_generate_learning_material_when_week_type_is_regular(mock_db):
    result = MagicMock()
    result.all.return_value = [
        (mock_db.plan, mock_db.week_1)
    ]
    mock_db.execute = AsyncMock(return_value=result)

    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[1],
        concurrency=1,
        include_resources=False,
    )

    assert len(results) == 1
    assert results[0].content_type == "LEARNING_MATERIAL"
    assert results[0].ctx.week == 1
    assert results[0].ctx.week_data.week_type == "regular"

@pytest.mark.asyncio
async def test_generate_contents_without_week_numbers(mock_db):
    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=None,
        concurrency=1,
    )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_generate_contents_specific_weeks(mock_db):
    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[1, 3],
        concurrency=1,
        include_resources=False,
    )

    assert len(results) == 2

    generated_weeks = {
        result.ctx.week for result in results
    }

    assert generated_weeks == {1, 3}

    for result in results:
        assert result.content_type == "LEARNING_MATERIAL"
        assert result.error is None


@pytest.mark.asyncio
async def test_generate_contents_with_additional_prompt(mock_db):
    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[1],
        concurrency=1,
        additional_prompt="Jelaskan materi dengan contoh praktis.",
    )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_generate_contents_with_concurrency(mock_db):
    results = await generate_contents(
        db=mock_db,
        course_plan_id="courseplan000000000001",
        week_numbers=[1, 2],
        concurrency=2,
    )

    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_generate_contents_invalid_course_plan(mock_db):
    with patch(
        "src.services.content.generate_service.ContentGenerationRepository.get_context",
        new_callable=AsyncMock,
        return_value=None,
    ):
        with pytest.raises(ContentGenerationError):
            await generate_contents(
                db=mock_db,
                course_plan_id="invalid_courseplan",
            )
