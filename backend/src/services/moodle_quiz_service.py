"""Operasi quiz ke Moodle (BE-12.3).

Isi quiz diambil dari ``QuizData`` (``activities.activity_data``, lihat
:mod:`src.schemas.content`): deskripsi, konfigurasi, dan soal pilihan ganda
beserta kunci jawaban (Content Schema §17–§19). Quiz dipublikasikan melalui
plugin ``local_capstonebridge`` (minimal versi 0.5.0) pada section sesuai nomor
minggu. Soal dibuat pada question bank course, dalam satu kategori per quiz,
lalu ditambahkan ke quiz.

Pemetaan konfigurasi:

* ``time_limit_minutes``: batas waktu quiz; ``None`` berarti tanpa batas;
* ``max_attempts``: jumlah attempt yang diizinkan;
* ``passing_score_percent``: nilai lulus dari skala 0–100; ``None`` berarti tidak diatur;
* ``shuffle_questions``: urutan soal diacak untuk setiap attempt.

Pengaturan lain memakai nilai tetap plugin (lihat README plugin): satu soal per
halaman, opsi jawaban diacak, dan pembahasan tampil setelah attempt dikirim.

Idempotency sama seperti resource dan assignment: ``cmid`` disimpan di tabel
``moodle_entity_mappings``, dan idempotency key disimpan sebagai *ID number*
activity serta *ID number* kategori soal. Eksekusi ulang memperbarui quiz dan
mengganti soalnya. Bila mahasiswa sudah mengerjakan quiz, soal tidak diganti
agar jawaban dan nilai tidak rusak; hanya judul, deskripsi, konfigurasi, dan
section yang diperbarui, dan hasil operasi menandai ``questions_replaced=False``.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.schemas.content import QuizData
from src.services.moodle_client import MoodleClient
from src.services.moodle_mapping import IMoodleMappingRepository, MoodleMapping

__all__ = [
    "QUIZ_ENTITY_TYPE",
    "InvalidQuizError",
    "MoodleQuizService",
    "QuizContent",
    "QuizOption",
    "QuizPublishResult",
    "QuizQuestion",
    "QuizSettings",
    "quiz_idempotency_key",
]

QUIZ_ENTITY_TYPE = "quiz"
CREATE_FUNCTION = "local_capstonebridge_create_quiz"
UPDATE_FUNCTION = "local_capstonebridge_update_quiz"

_IDEMPOTENCY_PREFIX = "capstone-quiz-"
_MAX_IDNUMBER_LENGTH = 100  # panjang kolom course_modules.idnumber di Moodle
_MAX_NAME_LENGTH = 255


class InvalidQuizError(ValueError):
    """Data quiz atau konfigurasinya tidak valid."""


@dataclass(frozen=True)
class QuizOption:
    key: str
    text: str


@dataclass(frozen=True)
class QuizQuestion:
    question_text: str
    options: tuple[QuizOption, ...]
    correct_option_key: str
    explanation: str = ""


@dataclass(frozen=True)
class QuizSettings:
    """Konfigurasi quiz (Content Schema §19)."""

    time_limit_minutes: int | None = None
    max_attempts: int = 1
    shuffle_questions: bool = False
    passing_score_percent: int | None = None

    def to_moodle(self) -> dict[str, int]:
        return {
            "timelimit": (self.time_limit_minutes or 0) * 60,
            "attempts": self.max_attempts,
            "passpercent": self.passing_score_percent or 0,
            "shufflequestions": int(self.shuffle_questions),
        }


@dataclass(frozen=True)
class QuizContent:
    """Quiz hasil generation (Content Schema §17)."""

    id: str
    title: str
    description: str
    questions: tuple[QuizQuestion, ...]
    settings: QuizSettings = QuizSettings()

    @classmethod
    def from_activity(
        cls, activity_id: str, title: str, activity_data: Mapping[str, Any]
    ) -> QuizContent:
        """Bangun dari baris ``activities`` bertipe ``QUIZ``."""
        try:
            data = QuizData.model_validate(dict(activity_data))
        except ValidationError as exc:
            raise InvalidQuizError(f"activity_data quiz tidak valid: {exc}") from exc
        return cls(
            id=str(activity_id),
            title=title,
            description=data.description,
            questions=tuple(
                QuizQuestion(
                    question_text=item.question_text,
                    options=tuple(QuizOption(option.key, option.text) for option in item.options),
                    correct_option_key=item.correct_option_key,
                    explanation=item.explanation,
                )
                for item in data.questions
            ),
            settings=QuizSettings(
                time_limit_minutes=data.config.time_limit_minutes,
                max_attempts=data.config.max_attempts,
                shuffle_questions=data.config.shuffle_questions,
                passing_score_percent=data.config.passing_score_percent,
            ),
        )


@dataclass(frozen=True)
class QuizPublishResult:
    quiz_id: str
    moodle_course_id: int
    week: int
    cmid: int
    instance_id: int
    idempotency_key: str
    created: bool
    question_count: int
    questions_replaced: bool
    has_attempts: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "quiz_id": self.quiz_id,
            "moodle_course_id": self.moodle_course_id,
            "week": self.week,
            "cmid": self.cmid,
            "instance_id": self.instance_id,
            "idempotency_key": self.idempotency_key,
            "created": self.created,
            "question_count": self.question_count,
            "questions_replaced": self.questions_replaced,
            "has_attempts": self.has_attempts,
        }


def quiz_idempotency_key(quiz_id: str) -> str:
    """Idempotency key yang disimpan sebagai ID number quiz dan kategori soalnya."""
    return f"{_IDEMPOTENCY_PREFIX}{quiz_id}"


class MoodleQuizService:
    def __init__(self, client: MoodleClient, mappings: IMoodleMappingRepository) -> None:
        self._client = client
        self._mappings = mappings

    async def publish(self, moodle_course_id: int, week: int, quiz: QuizContent) -> QuizPublishResult:
        """Buat quiz beserta soalnya pada section minggu ``week``, atau perbarui bila sudah ada."""
        _validate(moodle_course_id, week, quiz)
        key = quiz_idempotency_key(quiz.id)
        fields = {
            "courseid": moodle_course_id,
            "name": quiz.title.strip(),
            "intro": _paragraphs(quiz.description),
            "questions": [_question_payload(question) for question in quiz.questions],
            **quiz.settings.to_moodle(),
        }

        cmid = await self._mappings.get_moodle_id(QUIZ_ENTITY_TYPE, quiz.id)
        created = False
        if cmid is None:
            result = await self._client.call(
                CREATE_FUNCTION, {**fields, "section": week, "idnumber": key}
            )
            cmid = int(result["cmid"])
            created = int(result["created"]) == 1
            if not created:
                # Quiz sudah ada di Moodle (eksekusi sebelumnya terhenti sebelum
                # mapping tersimpan): samakan isinya dengan data terbaru.
                result = await self._update(cmid, week, fields)
            await self._mappings.save(MoodleMapping(QUIZ_ENTITY_TYPE, quiz.id, cmid))
        else:
            result = await self._update(cmid, week, fields)

        return QuizPublishResult(
            quiz_id=quiz.id,
            moodle_course_id=moodle_course_id,
            week=week,
            cmid=cmid,
            instance_id=int(result["instanceid"]),
            idempotency_key=key,
            created=created,
            question_count=int(result["questioncount"]),
            questions_replaced=created or int(result.get("questionsreplaced", 0)) == 1,
            has_attempts=int(result.get("hasattempts", 0)) == 1,
        )

    async def _update(self, cmid: int, week: int, fields: dict[str, Any]) -> dict[str, Any]:
        return await self._client.call(UPDATE_FUNCTION, {**fields, "cmid": cmid, "section": week})


def _validate(moodle_course_id: int, week: int, quiz: QuizContent) -> None:
    if moodle_course_id <= 0:
        raise InvalidQuizError("moodle_course_id harus bilangan positif")
    if week < 0:
        raise InvalidQuizError("nomor minggu tidak boleh negatif")
    if not quiz.id.strip():
        raise InvalidQuizError("quiz wajib memiliki id")
    if len(quiz_idempotency_key(quiz.id)) > _MAX_IDNUMBER_LENGTH:
        raise InvalidQuizError("id quiz terlalu panjang untuk idempotency key")
    if not quiz.title.strip():
        raise InvalidQuizError("judul quiz wajib diisi")
    if len(quiz.title.strip()) > _MAX_NAME_LENGTH:
        raise InvalidQuizError("judul quiz maksimal 255 karakter")
    if not quiz.questions:
        raise InvalidQuizError("quiz wajib memiliki minimal satu soal")

    for number, question in enumerate(quiz.questions, start=1):
        if not question.question_text.strip():
            raise InvalidQuizError(f"soal {number} tidak memiliki teks")
        if len(question.options) < 2:
            raise InvalidQuizError(f"soal {number} wajib memiliki minimal dua opsi")
        keys = [option.key for option in question.options]
        if len(set(keys)) != len(keys):
            raise InvalidQuizError(f"key opsi soal {number} harus unik")
        if question.correct_option_key not in keys:
            raise InvalidQuizError(f"kunci jawaban soal {number} tidak ada di opsi")
        if any(not option.text.strip() for option in question.options):
            raise InvalidQuizError(f"soal {number} memiliki opsi kosong")

    settings = quiz.settings
    if settings.time_limit_minutes is not None and settings.time_limit_minutes < 1:
        raise InvalidQuizError("time_limit_minutes minimal 1 atau kosong")
    if settings.max_attempts < 1:
        raise InvalidQuizError("max_attempts minimal 1")
    if settings.passing_score_percent is not None and not 0 <= settings.passing_score_percent <= 100:
        raise InvalidQuizError("passing_score_percent harus 0 sampai 100")


def _question_payload(question: QuizQuestion) -> dict[str, Any]:
    return {
        "text": _paragraphs(question.question_text),
        "generalfeedback": _paragraphs(question.explanation),
        "answers": [
            {"text": option.text.strip(), "correct": int(option.key == question.correct_option_key)}
            for option in question.options
        ],
    }


def _paragraphs(text: str) -> str:
    """Teks biasa menjadi paragraf HTML yang sudah di-escape."""
    parts = [part.strip() for part in text.strip().split("\n\n") if part.strip()]
    return "".join("<p>" + "<br>".join(html.escape(line.strip()) for line in part.splitlines()) + "</p>" for part in parts)