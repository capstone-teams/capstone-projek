"""Schema aktivitas yang ditambahkan dosen langsung dari halaman kursus.

Dua endpoint di bawah ``/integrations/moodle/courses/{id}/activities``:

- ``POST .../activities``: membuat Assignment, Quiz, atau Text and media area
  pada satu section lewat function plugin ``local_capstonebridge`` yang sudah
  dipakai eksekusi Moodle (``create_assign``, ``create_quiz``, ``create_page``).
  Text and media area dibuat sebagai Page sehingga tidak perlu memasang ulang
  plugin; isinya tetap tampil langsung di kartu minggu pada halaman kursus;
- ``POST .../activities/generate``: draf isi aktivitas dari AI berdasarkan
  materi minggu tersebut, RPS kursus, dan file referensi pilihan dosen. Draf
  hanya mengisi formulir; aktivitas baru dibuat setelah dosen menyimpannya.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.schemas.content import MaterialIllustration


class ActivityModname(str, Enum):
    ASSIGN = "assign"
    QUIZ = "quiz"
    LABEL = "label"


class QuizAnswerIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    correct: bool = False


class QuizQuestionIn(BaseModel):
    text: str = Field(min_length=1, max_length=10000, description="Teks soal (HTML atau teks biasa).")
    generalfeedback: str = Field(default="", max_length=10000, description="Pembahasan soal.")
    answers: list[QuizAnswerIn] = Field(min_length=2, max_length=10)

    @model_validator(mode="after")
    def _one_correct(self) -> QuizQuestionIn:
        if sum(1 for answer in self.answers if answer.correct) != 1:
            raise ValueError("setiap soal wajib memiliki tepat satu jawaban benar")
        return self


class CreateActivityRequest(BaseModel):
    """Isian formulir "New <aktivitas>"; field yang tidak relevan untuk jenisnya diabaikan."""

    model_config = ConfigDict(extra="forbid")

    section: int = Field(ge=0, description="Nomor section (0 = umum).")
    modname: ActivityModname
    name: str = Field(default="", max_length=255)
    intro: str = Field(default="", max_length=200_000, description="Deskripsi Assignment/Quiz (HTML).")
    text: str = Field(default="", max_length=200_000, description="Isi Text and media area (HTML).")
    # Assignment (pengaturan yang didukung create_assign plugin terpasang)
    duedate: int = Field(default=0, ge=0)
    grade: int = Field(default=100, ge=1, le=100)
    onlinetext_enabled: bool = False
    file_enabled: bool = True
    file_maxfiles: int = Field(default=1, ge=1, le=20)
    # Quiz
    timelimit_minutes: int = Field(default=0, ge=0)
    attempts: int = Field(default=1, ge=0)
    passpercent: int = Field(default=0, ge=0, le=100)
    shufflequestions: bool = False
    questions: list[QuizQuestionIn] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def _required_per_kind(self) -> CreateActivityRequest:
        if self.modname in (ActivityModname.ASSIGN, ActivityModname.QUIZ) and not self.name.strip():
            raise ValueError("name wajib diisi untuk assignment dan quiz")
        if self.modname is ActivityModname.LABEL and not self.text.strip():
            raise ValueError("text wajib diisi untuk text and media area")
        if self.modname is ActivityModname.ASSIGN:
            if not (self.onlinetext_enabled or self.file_enabled):
                raise ValueError("pilih minimal satu jenis pengumpulan")
        if self.modname is ActivityModname.QUIZ and not self.questions:
            raise ValueError("quiz wajib memiliki minimal satu soal")
        return self


class CreateActivityResponse(BaseModel):
    cmid: int
    modname: ActivityModname
    section: int
    created: bool


# --- Generate (draf AI) -----------------------------------------------------


class GeneratedQuizOption(BaseModel):
    key: str
    text: str


class GeneratedQuizQuestion(BaseModel):
    question_text: str
    options: list[GeneratedQuizOption]
    correct_option_key: str
    explanation: str


class GenerateActivityResponse(BaseModel):
    """Draf isian formulir; dosen dapat mengubahnya sebelum menyimpan."""

    modname: ActivityModname
    name: str
    intro: str = Field(default="", description="Deskripsi Assignment/Quiz (HTML).")
    text: str = Field(default="", description="Isi Text and media area (HTML, termasuk ilustrasi).")
    questions: list[GeneratedQuizQuestion] = Field(default_factory=list)
    references_used: list[str] = Field(default_factory=list, description="Referensi yang dipakai AI.")


# Output LLM (structured output, strict) ------------------------------------


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RubricRow(_Strict):
    criterion: str = Field(min_length=1)
    description: str = Field(min_length=1)
    weight_percent: int


class AssignmentDraftOutput(_Strict):
    name: str = Field(min_length=1, max_length=255)
    instructions_markdown: str = Field(min_length=1)
    expected_outputs: list[str]
    rubric: list[RubricRow]


class QuizDraftOutput(_Strict):
    name: str = Field(min_length=1, max_length=255)
    description: str
    questions: list[GeneratedQuizQuestion] = Field(min_length=1)


class LabelDraftOutput(_Strict):
    name: str = Field(min_length=1, max_length=255)
    body_markdown: str = Field(min_length=1)
    illustration: MaterialIllustration | None = None
