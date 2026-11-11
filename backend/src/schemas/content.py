"""Output schema konten, disesuaikan dengan tabel `contents` dan `activities`.

Tiga lapis model per jenis konten:

  XxxBody    -> isi inti konten (field yang dihasilkan LLM, tanpa metadata)
  XxxOutput  -> Body + title + sub_cpmk_codes          (kontrak dengan LLM / structured output)
  XxxData    -> Body + traceability lengkap            (isi kolom JSONB: content_data / activity_data)

Pemetaan ke database:

  LEARNING_MATERIAL -> contents    (title, content_data, content_markdown)
  RESOURCE          -> contents    (title, content_data)
  ASSIGNMENT        -> activities  (title, activity_data)
  QUIZ              -> activities  (title, activity_data)

Traceability:
  - sub_cpmk_codes  : dihasilkan LLM (tidak punya kolom di DB)
  - week_number     : diisi backend dari WeekContext
  - weekly_plan_ref : diisi backend dari WeekContext.course_plan_week_id
  LLM tidak diminta mengisi nomor minggu / id weekly plan agar tidak halusinasi.

Aturan OpenAI strict: extra="forbid", tanpa default value, opsional = `X | None`.
Aturan bisnis ada di validator Pydantic (dijalankan setelah respons LLM diterima).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ==========================================
# INPUT CONTEXT
# ==========================================
class WeeklyContentContext(BaseModel):
    week_number: int = Field(ge=1)
    week_type: str = "regular"
    title: str | None = None
    learning_outcomes: Any = None
    topics: list[Any] = Field(default_factory=list)
    methods: list[Any] = Field(default_factory=list)
    assessment: Any = None


class WeekContext(BaseModel):
    course_plan_id: str
    course_plan_week_id: str
    week_number: int = Field(ge=1)
    week_data: WeeklyContentContext
    # Minggu-minggu sebelumnya yang dicakup minggu ini (mis. kuis). Diisi oleh service.
    covered_weeks: list[WeeklyContentContext] = Field(default_factory=list)

    @property
    def week(self) -> int:
        return self.week_number

    def to_prompt_dict(self) -> dict:
        data = {
            "course_plan_id": self.course_plan_id,
            "course_plan_week_id": self.course_plan_week_id,
            "week_number": self.week_number,
            "week_data": self.week_data.model_dump(mode="json"),
        }
        if self.covered_weeks:
            data["covered_weeks"] = [w.model_dump(mode="json") for w in self.covered_weeks]
        return data


# ==========================================
# ENUM (nilai sama dengan enum di model database)
# ==========================================
class ContentType(str, Enum):  # tabel contents
    LEARNING_MATERIAL = "LEARNING_MATERIAL"
    RESOURCE = "RESOURCE"


class ActivityType(str, Enum):  # tabel activities
    ASSIGNMENT = "ASSIGNMENT"
    QUIZ = "QUIZ"


class ResourceKind(str, Enum):
    ARTICLE = "ARTICLE"
    VIDEO = "VIDEO"
    JOURNAL = "JOURNAL"
    BOOK = "BOOK"
    DOCUMENTATION = "DOCUMENTATION"
    TOOL = "TOOL"
    OTHER = "OTHER"


# ==========================================
# BASE & TRACEABILITY (§23)
# ==========================================
class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Traceability(_Strict):
    """Disimpan di dalam content_data / activity_data."""

    week_number: int = Field(ge=1)
    sub_cpmk_codes: list[str] = Field(min_length=1)
    weekly_plan_ref: str = Field(min_length=1)


class _OutputMixin(_Strict):
    """Field metadata yang diminta dari LLM pada setiap jenis konten."""

    title: str = Field(min_length=1, max_length=255)
    sub_cpmk_codes: list[str] = Field(min_length=1)


class _DataMixin(_Strict):
    """Field metadata yang disimpan di kolom JSONB."""

    traceability: Traceability


# ==========================================
# 1. LEARNING MATERIAL  -> contents
# ==========================================
class IllustrationKind(str, Enum):
    DIAGRAM = "DIAGRAM"  # diagram Mermaid, dirender menjadi SVG
    PHOTO = "PHOTO"  # gambar berlisensi bebas dari Wikimedia Commons


class MaterialIllustration(_Strict):
    """Ilustrasi satu section materi.

    LLM hanya mengisi ``kind``, ``caption``, dan ``mermaid`` (DIAGRAM) atau
    ``image_query`` (PHOTO). ``image_url``, ``source_url``, dan ``attribution``
    selalu diisi ulang backend (lihat :mod:`src.services.content.illustrations`),
    sehingga URL dari LLM tidak pernah dipakai.
    """

    kind: IllustrationKind
    caption: str = Field(min_length=1, max_length=300)
    mermaid: str | None = None
    image_query: str | None = None
    image_url: str | None = None
    source_url: str | None = None
    attribution: str | None = None


class MaterialSection(_Strict):
    heading: str = Field(min_length=1)
    body_markdown: str = Field(min_length=1)
    # Default None agar content_data lama (sebelum ilustrasi) tetap valid; strict schema LLM tetap mewajibkannya.
    illustration: MaterialIllustration | None = None


class MaterialReference(_Strict):
    title: str = Field(min_length=1)
    url: str | None  # null bila sumber tidak punya URL


class LearningMaterialBody(_Strict):
    learning_objectives: list[str] = Field(min_length=1)
    sections: list[MaterialSection] = Field(min_length=1)
    references: list[MaterialReference]  # boleh kosong; berasal dari RPS / learning resource


class LearningMaterialOutput(LearningMaterialBody, _OutputMixin):
    pass


class LearningMaterialData(LearningMaterialBody, _DataMixin):
    pass


def render_material_markdown(body: LearningMaterialBody) -> str:
    """Isi kolom contents.content_markdown (dikonversi ke HTML di BE-21.1)."""
    parts = []
    if body.learning_objectives:
        objectives = "\n".join(f"- {o}" for o in body.learning_objectives)
        parts.append(f"## Tujuan Pembelajaran\n\n{objectives}")
    parts += [f"## {s.heading}\n\n{s.body_markdown}" for s in body.sections]
    if body.references:
        refs = "\n".join(
            f"- [{r.title}]({r.url})" if r.url else f"- {r.title}" for r in body.references
        )
        parts.append(f"## Referensi\n\n{refs}")
    return "\n\n".join(parts)


# ==========================================
# 2. LEARNING RESOURCE  -> contents
# ==========================================
class ResourceBody(_Strict):
    url: str | None  # null bila URL tidak dapat dipastikan
    description: str = Field(min_length=1)
    resource_kind: ResourceKind
    relevance_reason: str = Field(min_length=1)


class ResourceOutput(ResourceBody, _OutputMixin):
    pass


class ResourceData(ResourceBody, _DataMixin):
    pass


# ==========================================
# 3. ASSIGNMENT  -> activities
# ==========================================
class RubricCriterion(_Strict):
    criterion: str = Field(min_length=1)
    description: str = Field(min_length=1)
    weight_percent: int = Field(ge=1, le=100)


class AssignmentBody(_Strict):
    instructions_markdown: str = Field(min_length=1)
    expected_outputs: list[str] = Field(min_length=1)
    rubric: list[RubricCriterion] = Field(min_length=1)

    @model_validator(mode="after")
    def _rubric_total_100(self):
        total = sum(c.weight_percent for c in self.rubric)
        if total != 100:
            raise ValueError(f"Total bobot rubrik harus 100, saat ini {total}")
        return self


class AssignmentOutput(AssignmentBody, _OutputMixin):
    pass


class AssignmentData(AssignmentBody, _DataMixin):
    pass


# ==========================================
# 4. QUIZ  -> activities
# ==========================================
class QuizConfig(_Strict):
    time_limit_minutes: int | None = Field(ge=1)
    max_attempts: int = Field(ge=1)
    shuffle_questions: bool
    passing_score_percent: int | None = Field(ge=0, le=100)


class QuizOption(_Strict):
    key: str = Field(min_length=1, max_length=2)  # "A", "B", ...
    text: str = Field(min_length=1)


class QuizQuestion(_Strict):
    question_text: str = Field(min_length=1)
    options: list[QuizOption] = Field(min_length=2)
    correct_option_key: str = Field(min_length=1, max_length=2)
    explanation: str = Field(min_length=1)

    @model_validator(mode="after")
    def _check_options(self):
        keys = [o.key for o in self.options]
        if len(set(keys)) != len(keys):
            raise ValueError("Key opsi harus unik")
        if self.correct_option_key not in keys:
            raise ValueError("correct_option_key tidak ada di options")
        return self


class QuizBody(_Strict):
    description: str = Field(min_length=1)
    config: QuizConfig
    questions: list[QuizQuestion] = Field(min_length=1)


class QuizOutput(QuizBody, _OutputMixin):
    pass


class QuizData(QuizBody, _DataMixin):
    pass


# ==========================================
# REGISTRY: jenis konten -> model & tabel
# ==========================================
@dataclass(frozen=True)
class ContentSpec:
    output_model: type[BaseModel]
    data_model: type[BaseModel]
    table: str  # "contents" | "activities"


REGISTRY: dict[str, ContentSpec] = {
    ContentType.LEARNING_MATERIAL.value: ContentSpec(LearningMaterialOutput, LearningMaterialData, "contents"),
    ContentType.RESOURCE.value: ContentSpec(ResourceOutput, ResourceData, "contents"),
    ActivityType.ASSIGNMENT.value: ContentSpec(AssignmentOutput, AssignmentData, "activities"),
    ActivityType.QUIZ.value: ContentSpec(QuizOutput, QuizData, "activities"),
}


# ==========================================
# MAPPER: Output LLM -> kwargs baris database
# ==========================================
def build_traceability(ctx: WeekContext, sub_cpmk_codes: list[str]) -> Traceability:
    return Traceability(
        week_number=ctx.week_number,
        sub_cpmk_codes=sub_cpmk_codes,
        weekly_plan_ref=ctx.course_plan_week_id,
    )


def to_data(key: str, output: BaseModel, ctx: WeekContext) -> BaseModel:
    """Output LLM -> model Data (isi kolom JSONB)."""
    spec = REGISTRY[key]
    body = output.model_dump(mode="json", exclude={"title", "sub_cpmk_codes"})
    trace = build_traceability(ctx, output.sub_cpmk_codes)  # type: ignore[attr-defined]
    return spec.data_model.model_validate({**body, "traceability": trace.model_dump()})


def to_row(
    key: str,
    output: BaseModel,
    ctx: WeekContext,
    agent_run_id: str | None = None,
) -> dict[str, Any]:
    """Kwargs untuk Content(...) atau Activity(...) sesuai jenisnya."""
    spec = REGISTRY[key]
    data = to_data(key, output, ctx)
    payload = data.model_dump(mode="json")
    title = output.title  # type: ignore[attr-defined]

    if spec.table == "contents":
        return {
            "course_plan_week_id": ctx.course_plan_week_id,
            "title": title,
            "content_type": key,
            "content_data": payload,
            "content_markdown": (
                render_material_markdown(data)  # type: ignore[arg-type]
                if key == ContentType.LEARNING_MATERIAL.value
                else None
            ),
            "generated_by_agent_run_id": agent_run_id,
        }
    return {
        "course_plan_week_id": ctx.course_plan_week_id,
        "type": key,
        "title": title,
        "activity_data": payload,
    }


def from_row(key: str, title: str, data: dict) -> BaseModel:
    """Baca kolom JSONB dari DB -> model Data (untuk tampilan review / eksekusi Moodle)."""
    return REGISTRY[key].data_model.model_validate(data)


# ==========================================
# EKSPOR JSON SCHEMA (OpenAI structured output)
# ==========================================
_UNSUPPORTED = {
    "minLength", "maxLength", "minItems", "maxItems",
    "minimum", "maximum", "default", "title",
}


def _clean(node: Any) -> Any:
    if isinstance(node, dict):
        out = {k: _clean(v) for k, v in node.items() if k not in _UNSUPPORTED}
        if "properties" in node:  # properti bernama "title" harus tetap ada
            out["properties"] = {k: _clean(v) for k, v in node["properties"].items()}
        if out.get("type") == "object" and "properties" in out:
            out["additionalProperties"] = False
            out["required"] = list(out["properties"].keys())
        return out
    if isinstance(node, list):
        return [_clean(i) for i in node]
    return node


def export_json_schema(model: type[BaseModel]) -> dict:
    return _clean(model.model_json_schema())


def to_response_format(key: str) -> dict:
    """response_format OpenAI untuk satu jenis konten, mis. to_response_format("QUIZ")."""
    model = REGISTRY[key].output_model
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"generated_{key.lower()}",
            "strict": True,
            "schema": export_json_schema(model),
        },
    }


# ==========================================
# CONTOH DATA VALID
# ==========================================
# Format OUTPUT LLM (title + sub_cpmk_codes, tanpa week_number / weekly_plan_ref)
OUTPUT_EXAMPLES: dict[str, dict] = {
    "LEARNING_MATERIAL": {
        "title": "Normalisasi Basis Data",
        "sub_cpmk_codes": ["Sub-CPMK-3.1"],
        "learning_objectives": [
            "Menjelaskan tujuan normalisasi",
            "Menerapkan 1NF sampai 3NF pada tabel sederhana",
        ],
        "sections": [
            {"heading": "Pengantar", "body_markdown": "Normalisasi mengurangi **redundansi** data."},
            {
                "heading": "Bentuk Normal Pertama (1NF)",
                "body_markdown": "Setiap kolom hanya berisi nilai atomik.\n\n- Tidak ada grup berulang",
            },
        ],
        "references": [
            {"title": "Database Normalization Explained", "url": "https://example.com/normalization"},
        ],
    },
    "RESOURCE": {
        "title": "Database Normalization Explained",
        "sub_cpmk_codes": ["Sub-CPMK-3.1"],
        "url": "https://example.com/normalization",
        "description": "Penjelasan bertahap 1NF-3NF dengan contoh.",
        "resource_kind": "ARTICLE",
        "relevance_reason": "Melengkapi materi minggu 3 dengan contoh tambahan.",
    },
    "ASSIGNMENT": {
        "title": "Normalisasi Studi Kasus Perpustakaan",
        "sub_cpmk_codes": ["Sub-CPMK-3.1"],
        "instructions_markdown": "Normalkan tabel peminjaman buku hingga **3NF**.",
        "expected_outputs": ["Dokumen PDF berisi tahapan normalisasi", "Diagram ERD akhir"],
        "rubric": [
            {"criterion": "Ketepatan 1NF-3NF", "description": "Tahapan benar dan lengkap", "weight_percent": 60},
            {"criterion": "Kualitas ERD", "description": "Relasi dan kardinalitas tepat", "weight_percent": 40},
        ],
    },
    "QUIZ": {
        "title": "Kuis Normalisasi",
        "sub_cpmk_codes": ["Sub-CPMK-3.1"],
        "description": "Kuis singkat pemahaman 1NF-3NF.",
        "config": {
            "time_limit_minutes": 15,
            "max_attempts": 2,
            "shuffle_questions": True,
            "passing_score_percent": 70,
        },
        "questions": [
            {
                "question_text": "Tabel disebut memenuhi 1NF jika...",
                "options": [
                    {"key": "A", "text": "Semua kolom bernilai atomik"},
                    {"key": "B", "text": "Tidak ada primary key"},
                    {"key": "C", "text": "Semua kolom nullable"},
                    {"key": "D", "text": "Tidak ada foreign key"},
                ],
                "correct_option_key": "A",
                "explanation": "1NF mensyaratkan nilai atomik dan tidak ada grup berulang.",
            }
        ],
    },
}

EXAMPLE_CTX = WeekContext(
    course_plan_id="cp_001",
    course_plan_week_id="cpw_0003",
    week_number=3,
    week_data=WeeklyContentContext(week_number=3, title="Normalisasi"),
)


def stored_examples() -> dict[str, dict]:
    """Contoh baris DB (acuan mock Backend API / Frontend)."""
    out = {}
    for key, raw in OUTPUT_EXAMPLES.items():
        output = REGISTRY[key].output_model.model_validate(raw)
        out[key] = to_row(key, output, EXAMPLE_CTX)
    return out


if __name__ == "__main__":
    import json

    for key, spec in REGISTRY.items():
        output = spec.output_model.model_validate(OUTPUT_EXAMPLES[key])
        row = to_row(key, output, EXAMPLE_CTX)
        payload = row.get("content_data") or row.get("activity_data")
        from_row(key, row["title"], payload)  # round-trip
        json.dumps(to_response_format(key))
        print("OK", key, "->", spec.table)
