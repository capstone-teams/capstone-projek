"""RPS Structured Data Schema (BE-05.3) — kontrak data hasil ekstraksi RPS.

Modul ini adalah **kontrak bersama backend dan AI** untuk tahap ekstraksi
(BE-08): bentuk data yang harus dihasilkan ketika sebuah RPS diubah menjadi
struktur akademik. Rujukan desain:

- ``docs/02. design/content-schema.md`` §6 (RPS Analysis Schema) dan §7 (RPS
  Week Schema) — bentuk object dan nama field;
- §44 (Schema Evolution) — ``schema_version`` sebagai versi skema, terpisah dari
  content version;
- §45 (JSON Schema Implementation) — Pydantic sebagai definisi schema
  application-level;
- §3.2 (Schema is a Contract) — setiap output agent wajib melewati validasi
  schema sebelum disimpan/diteruskan;
- §3.4 (Extensible but Controlled) — field utama eksplisit, tanpa wadah
  ``additional_data`` yang menampung apa pun.

Aturan bentuk yang dipegang modul ini:

1. **Tidak ada field akademik yang wajib diisi.** RPS antar-program studi
   berbeda-beda, sehingga field yang tidak tersedia pada dokumen bernilai
   ``None`` atau list kosong (§6/§7: "boleh kosong atau null"). Yang wajib
   hanyalah *isi* dari sebuah entri yang memang ada — misalnya sebuah learning
   outcome harus punya ``description``, tetapi dokumen boleh tidak memiliki
   learning outcome sama sekali.
2. **Sistem tidak boleh mengarang.** Tidak ada nilai default berupa teks
   placeholder: field yang tidak ditemukan tetap kosong, bukan diisi
   ``"TBD"``/``"N/A"`` hanya agar schema terlihat lengkap (§6).
3. **Strict terhadap field tak dikenal.** ``extra="forbid"`` diterapkan pada
   seluruh object supaya output agent yang menyimpang (salah nama field,
   menambah field di luar kontrak) gagal validasi — bukan diam-diam tersimpan
   setengah benar (§3.2, §3.4).
4. **Metadata persistence bukan bagian schema.** ``id``/``version``/
   ``created_at`` milik database dan tidak diulang di sini (§5: "Schema JSON
   tidak boleh menggantikan relational identity").

Pemetaan ke tabel ``rps_analyses`` (data-model §9) disediakan oleh
:func:`to_rps_analysis_payload` agar BE-08 tidak menebak nama kolom.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "RPS_SCHEMA_VERSION",
    "DanglingReference",
    "RPSAssessment",
    "RPSCourseIdentity",
    "RPSLearningOutcome",
    "RPSObjective",
    "RPSReference",
    "RPSStructuredData",
    "RPSStructuredModel",
    "RPSTopic",
    "RPSWeek",
    "RPSWeekAssessment",
    "to_rps_analysis_payload",
]

# Versi RPS Structured Data Schema yang berlaku (content-schema §44). Nilai ini
# ikut disimpan pada kolom ``rps.schema_version`` dan menjadi bagian dari kunci
# idempotency pemrosesan: dokumen dengan ``file_hash`` **dan**
# ``schema_version`` yang sama tidak diproses ulang (BE-05 acceptance criteria).
#
# Naikkan versi ini hanya bila bentuk schema berubah dan hasil lama tidak lagi
# dapat dipakai apa adanya (breaking → ``2.0``, backward-compatible → ``1.1``).
RPS_SCHEMA_VERSION = "1.0"


class RPSStructuredModel(BaseModel):
    """Base seluruh object RPS Structured Data.

    ``extra="forbid"`` dan bukan ``ignore``: schema ini adalah kontrak (§3.2),
    sehingga field di luar kontrak harus terlihat sebagai kegagalan validasi —
    bukan dibuang diam-diam. ``str_strip_whitespace`` membuang spasi di tepi
    nilai teks, karena output model bahasa sering membawa spasi tak sengaja.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("*", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        """Perlakukan string kosong/spasi sebagai "tidak tersedia" (``None``).

        Model bahasa kerap mengisi field yang tidak ditemukan dengan ``""``.
        Nilai semacam itu tidak membawa informasi akademik apa pun, sehingga
        dinormalkan menjadi ``None`` — bukan dibiarkan lolos sebagai teks kosong
        yang tampak seperti data.
        """
        if isinstance(value, str) and not value.strip():
            return None
        return value


class RPSCourseIdentity(RPSStructuredModel):
    """Identitas mata kuliah pada RPS (content-schema §6 ``course``)."""

    name: str | None = None
    code: str | None = None
    credits: int | None = Field(default=None, ge=0)
    semester: int | None = Field(default=None, ge=0)
    description: str | None = None


class RPSLearningOutcome(RPSStructuredModel):
    """Capaian pembelajaran (CPMK/LO) beserta kodenya bila RPS menyebutkannya.

    ``id`` opsional karena banyak RPS tidak memberi kode eksplisit; bila tidak
    ada, rujukan dari :class:`RPSWeek` cukup memakai deskripsinya sebagai teks.
    """

    id: str | None = None
    description: str = Field(min_length=1)


class RPSObjective(RPSStructuredModel):
    """Tujuan pembelajaran (OBJ) yang dinyatakan RPS."""

    id: str | None = None
    description: str = Field(min_length=1)


class RPSTopic(RPSStructuredModel):
    """Topik/bahan kajian yang dideklarasikan RPS."""

    id: str | None = None
    name: str = Field(min_length=1)


class RPSWeekAssessment(RPSStructuredModel):
    """Assessment satu minggu (content-schema §7 ``assessment``).

    Tidak diisi bila RPS tidak menentukan assessment untuk minggu tersebut —
    sistem tidak boleh mengarang assessment (§7).
    """

    type: str | None = None
    description: str | None = None


class RPSWeek(RPSStructuredModel):
    """Distribusi materi per minggu (content-schema §7).

    Sesuai §7, ``topics`` berisi **nama** topik, sedangkan
    ``learning_outcomes`` dan ``objectives`` berisi **kode** (``LO-1``,
    ``OBJ-1``) yang merujuk entri pada :class:`RPSStructuredData`.
    """

    week: int = Field(ge=1)
    topics: list[str] = Field(default_factory=list)
    learning_outcomes: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)
    # Nama field mengikuti content-schema §7 (``teaching_method``, tunggal).
    teaching_method: list[str] = Field(default_factory=list)
    assessment: RPSWeekAssessment | None = None

    @field_validator("topics", "learning_outcomes", "objectives", "teaching_method", mode="after")
    @classmethod
    def _drop_blank_entries(cls, value: list[str]) -> list[str]:
        """Buang entri kosong; entri tanpa isi bukan informasi akademik."""
        return [item for item in value if item]


class RPSAssessment(RPSStructuredModel):
    """Assessment tingkat mata kuliah (content-schema §6 ``assessments``).

    ``weight`` adalah bobot dalam persen bila RPS menyebutkannya; tidak diisi
    bila tidak ada, dan tidak pernah dikira-kira.
    """

    id: str | None = None
    type: str | None = None
    description: str | None = None
    week: int | None = Field(default=None, ge=1)
    weight: float | None = Field(default=None, ge=0, le=100)


class RPSReference(RPSStructuredModel):
    """Satu entri daftar pustaka/referensi (content-schema §6 ``references``)."""

    id: str | None = None
    citation: str = Field(min_length=1)
    authors: str | None = None
    year: int | None = None
    source: str | None = None


class DanglingReference(RPSStructuredModel):
    """Rujukan pada :class:`RPSWeek` yang tidak menemukan sasaran deklarasinya.

    Dilaporkan sebagai temuan (bukan error) oleh
    :meth:`RPSStructuredData.validate_references`, karena RPS yang berbeda
    memang boleh merujuk kode yang tidak dideklarasikan secara eksplisit.
    """

    week: int
    field: str
    value: str


class RPSStructuredData(RPSStructuredModel):
    """RPS Structured Data — kontrak lengkap hasil ekstraksi satu dokumen RPS.

    Seluruh field bersifat opsional dan boleh kosong; yang dijaga adalah
    konsistensi internal (nomor minggu tidak boleh duplikat) dan keutuhan entri.
    """

    schema_version: str = Field(default=RPS_SCHEMA_VERSION, min_length=1)
    course: RPSCourseIdentity = Field(default_factory=RPSCourseIdentity)
    learning_outcomes: list[RPSLearningOutcome] = Field(default_factory=list)
    objectives: list[RPSObjective] = Field(default_factory=list)
    topics: list[RPSTopic] = Field(default_factory=list)
    weeks: list[RPSWeek] = Field(default_factory=list)
    teaching_methods: list[str] = Field(default_factory=list)
    assessments: list[RPSAssessment] = Field(default_factory=list)
    references: list[RPSReference] = Field(default_factory=list)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _default_schema_version(cls, value: Any) -> Any:
        """Versi kosong berarti "tidak disebutkan": pakai versi yang berlaku.

        Producer (BE-08) boleh tidak mengirimkan ``schema_version`` sama sekali;
        nilai kosong tidak boleh menjadi versi kosong yang tak berarti. Validator
        ini sengaja idempoten terhadap :meth:`RPSStructuredModel._blank_to_none`
        sehingga urutan keduanya tidak memengaruhi hasil.
        """
        if value is None or (isinstance(value, str) and not value.strip()):
            return RPS_SCHEMA_VERSION
        return value

    @field_validator("teaching_methods", mode="after")
    @classmethod
    def _drop_blank_methods(cls, value: list[str]) -> list[str]:
        """Buang metode pengajaran kosong (lihat :meth:`RPSWeek._drop_blank_entries`)."""
        return [item for item in value if item]

    @model_validator(mode="after")
    def _reject_duplicate_weeks(self) -> RPSStructuredData:
        """Tolak nomor minggu duplikat.

        Dua entri untuk minggu yang sama membuat distribusi materi ambigu dan
        tidak dapat dipetakan ke satu ``course_plan_weeks`` (data-model §12).
        """
        seen: set[int] = set()
        duplicates: list[int] = []
        for week in self.weeks:
            if week.week in seen and week.week not in duplicates:
                duplicates.append(week.week)
            seen.add(week.week)
        if duplicates:
            listed = ", ".join(str(number) for number in sorted(duplicates))
            raise ValueError(f"nomor minggu duplikat pada RPS Structured Data: {listed}")
        return self

    def declared_ids(self, field: str) -> set[str]:
        """Kumpulan kode (``id``) yang dideklarasikan pada satu koleksi.

        ``field`` adalah nama koleksi tingkat dokumen: ``learning_outcomes``,
        ``objectives``, atau ``topics``. Entri tanpa ``id`` tidak menghasilkan
        kode apa pun, sehingga tidak dapat dirujuk lewat kode.
        """
        collection = getattr(self, field)
        return {entry.id for entry in collection if entry.id}

    def validate_references(self) -> list[DanglingReference]:
        """Temukan rujukan minggu yang tidak menemukan sasaran (§3.3).

        Traceability RPS (content-schema §3.3) mengharuskan setiap rencana
        mingguan dapat dikaitkan dengan Learning Outcome/Objective/Topic
        sumbernya. Pemeriksaan ini **tidak** melempar error: RPS yang berbeda
        boleh menyebut kode yang tidak dideklarasikan pada daftar utamanya, dan
        temuan ini dipakai sebagai bahan validasi (BE-09), bukan penghalang
        pemrosesan.
        """
        # `learning_outcomes`/`objectives` pada minggu berisi kode, sedangkan
        # `topics` berisi nama topik (content-schema §7) — sasaran pembandingnya
        # berbeda, jadi ditentukan per field.
        targets: dict[str, set[str]] = {
            "learning_outcomes": self.declared_ids("learning_outcomes"),
            "objectives": self.declared_ids("objectives"),
            "topics": {topic.name for topic in self.topics},
        }

        findings: list[DanglingReference] = []
        for week in self.weeks:
            for field, known in targets.items():
                # Koleksi sasaran kosong berarti tidak ada yang bisa dirujuk;
                # melaporkan seluruh rujukan minggu sebagai temuan hanya akan
                # menghasilkan derau, bukan sinyal traceability.
                if not known:
                    continue
                for value in getattr(week, field):
                    if value not in known:
                        findings.append(DanglingReference(week=week.week, field=field, value=value))
        return findings

    def has_academic_content(self) -> bool:
        """Apakah dokumen memuat informasi akademik apa pun.

        Dipakai untuk menolak hasil ekstraksi kosong sebagai kegagalan, bukan
        sebagai "RPS tanpa isi" yang tampak sah.
        """
        return any(
            (
                self.course.name,
                self.course.code,
                self.learning_outcomes,
                self.objectives,
                self.topics,
                self.weeks,
                self.teaching_methods,
                self.assessments,
                self.references,
            )
        )


def to_rps_analysis_payload(data: RPSStructuredData) -> dict[str, Any]:
    """Petakan RPS Structured Data ke kolom tabel ``rps_analyses``.

    Bentuk kolom mengikuti ``docs/02. design/data-model.md`` §9 dan
    ``src/models/rps_analysis.py``; kolom ``references`` pada database
    direpresentasikan sebagai ``references_data`` pada model ORM (nama
    ``references`` dipakai SQLAlchemy untuk terminologi relasi).

    Payload yang dikembalikan siap dipakai sebagai argumen kata kunci
    ``RPSAnalysis(...)``, sehingga BE-08 tidak perlu memetakan ulang:

    ```python
    payload = to_rps_analysis_payload(extracted)
    analysis = RPSAnalysis(rps_id=rps_id, version=1, **payload)
    ```
    """
    return {
        "course_identity": data.course.model_dump(mode="json"),
        "learning_outcomes": [entry.model_dump(mode="json") for entry in data.learning_outcomes],
        "objectives": [entry.model_dump(mode="json") for entry in data.objectives],
        "topics": [entry.model_dump(mode="json") for entry in data.topics],
        "weekly_distribution": [week.model_dump(mode="json") for week in data.weeks],
        "teaching_methods": list(data.teaching_methods),
        "assessments": [entry.model_dump(mode="json") for entry in data.assessments],
        "references_data": [entry.model_dump(mode="json") for entry in data.references],
        "raw_analysis": data.model_dump(mode="json"),
    }
