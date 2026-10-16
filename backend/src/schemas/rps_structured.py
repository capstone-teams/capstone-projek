"""RPS Structured Data Schema (BE-05.3) — kontrak data hasil ekstraksi RPS.

Modul ini adalah **kontrak bersama backend dan AI** untuk tahap ekstraksi
(BE-08): bentuk data yang harus dihasilkan ketika sebuah RPS diubah menjadi
struktur akademik. Rujukan desain:

- ``docs/02. design/content-schema.md`` §6.1 (RPS Analysis Schema) dan §6.2 (RPS
  Structured Data) — bentuk object dan nama field;
- §44 (Schema Evolution) — ``schema_version`` sebagai versi skema, terpisah dari
  content version;
- §45 (JSON Schema Implementation) — Pydantic sebagai definisi schema
  application-level;
- §3.2 (Schema is a Contract) — setiap output agent wajib melewati validasi
  schema sebelum disimpan/diteruskan;
- §3.3 (RPS Traceability) — rencana mingguan harus dapat dikaitkan ke sumber
  akademiknya;
- §3.4 (Extensible but Controlled) — field utama eksplisit, tanpa wadah
  ``additional_data`` yang menampung apa pun.

Hierarki capaian pembelajaran mengikuti template RPS program studi: **CPL**
(Capaian Pembelajaran Lulusan) → **CPMK** (Capaian Pembelajaran Mata Kuliah) →
**Sub-CPMK**. Inilah bentuk yang benar-benar tertulis pada dokumen RPS,
sehingga ekstraksi tidak perlu menebak pemetaan dari bentuk generik.

Aturan bentuk yang dipegang modul ini:

1. **Tidak ada field akademik yang wajib diisi.** RPS antar-program studi
   berbeda-beda, sehingga field yang tidak tersedia pada dokumen bernilai
   ``None`` atau list kosong (§6: "boleh kosong atau null"). Yang wajib hanyalah
   *isi* dari sebuah entri yang memang ada — misalnya sebuah CPL harus punya
   ``description``, tetapi dokumen boleh tidak memiliki CPL sama sekali.
2. **Sistem tidak boleh mengarang.** Tidak ada nilai default berupa teks
   placeholder: field yang tidak ditemukan tetap kosong, bukan diisi
   ``"TBD"``/``"N/A"`` hanya agar schema terlihat lengkap (§6).
3. **Strict terhadap field tak dikenal.** ``extra="forbid"`` diterapkan pada
   seluruh object supaya output agent yang menyimpang gagal validasi — bukan
   diam-diam tersimpan setengah benar (§3.2, §3.4).
4. **Rujukan silang dilaporkan, bukan dilarang.** Sub-CPMK → CPMK → CPL dan
   rujukan mingguan diperiksa oleh :meth:`RPSStructuredData.validate_references`
   dan menghasilkan *temuan* (§3.3). Format RPS berbeda-beda, sehingga rujukan
   yang tidak menemukan sasaran tidak boleh menggagalkan pemrosesan.
5. **Metadata persistence bukan bagian schema.** ``id``/``version``/
   ``created_at`` milik database dan tidak diulang di sini (§5: "Schema JSON
   tidak boleh menggantikan relational identity"). Yang *memang* bagian dari
   schema adalah :class:`RPSExtractionMetadata` — keterangan tentang proses
   ekstraksi itu sendiri, bukan identitas baris database.

Pemetaan ke tabel ``rps_analyses`` (data-model §9) disediakan oleh
:func:`to_rps_analysis_payload` agar BE-08 tidak menebak nama kolom.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

__all__ = [
    "RPS_SCHEMA_VERSION",
    "DanglingReference",
    "RPSAssessment",
    "RPSCourseIdentity",
    "RPSCourseOutcome",
    "RPSExtractionMetadata",
    "RPSGraduateOutcome",
    "RPSMedia",
    "RPSReference",
    "RPSStructuredData",
    "RPSStructuredModel",
    "RPSSubCourseOutcome",
    "RPSTopic",
    "RPSWeek",
    "RPSWeekAssessment",
    "RPSWeekType",
    "to_rps_analysis_payload",
]

# Versi RPS Structured Data Schema yang berlaku (content-schema §44). Nilai ini
# ikut disimpan pada kolom ``rps.schema_version`` dan menjadi bagian dari kunci
# idempotency pemrosesan: dokumen dengan ``file_hash`` **dan**
# ``schema_version`` yang sama tidak diproses ulang.
#
# Riwayat versi:
# - ``1.0`` — bentuk awal content-schema §6/§7 dengan
#   ``learning_outcomes``/``objectives`` generik;
# - ``2.0`` — hierarki capaian pembelajaran dibuat eksplisit (CPL/CPMK/Sub-CPMK),
#   ``week_type`` ditambahkan, ``weight`` menjadi ``weight_percent``, serta
#   ``media`` dan ``extraction`` tersedia. Perubahan ini *breaking* terhadap 1.0
#   (§44), sehingga hasil lama perlu diproses ulang sebelum dipakai pada skema
#   baru. Padanan field lama: ``learning_outcomes`` → ``cpmk``, ``objectives`` →
#   ``sub_cpmk``.
RPS_SCHEMA_VERSION = "2.0"


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


class RPSWeekType(str, Enum):
    """Jenis minggu pada rencana pembelajaran (content-schema §6.2).

    ``uts``/``uas`` menandai minggu ujian tengah/akhir semester, yang pada RPS
    umumnya tidak memuat materi baru.
    """

    REGULAR = "regular"
    UTS = "uts"
    UAS = "uas"


class RPSCourseIdentity(RPSStructuredModel):
    """Identitas mata kuliah pada RPS (content-schema §6.1 ``course``)."""

    name: str | None = None
    code: str | None = None
    credits: int | None = Field(default=None, ge=0)
    semester: int | None = Field(default=None, ge=0)
    description: str | None = None


class RPSGraduateOutcome(RPSStructuredModel):
    """CPL — Capaian Pembelajaran Lulusan (tingkat program studi).

    ``id`` adalah kode rujukan (mis. ``CPL-1``). RPS umumnya menuliskan kode
    langsung pada kolomnya, dan CPMK merujuk kode tersebut.
    """

    id: str | None = None
    description: str = Field(min_length=1)


class RPSCourseOutcome(RPSStructuredModel):
    """CPMK — Capaian Pembelajaran Mata Kuliah; merujuk satu atau lebih CPL."""

    id: str | None = None
    description: str = Field(min_length=1)
    cpl_ids: list[str] = Field(default_factory=list)

    @field_validator("cpl_ids", mode="after")
    @classmethod
    def _drop_blank_entries(cls, value: list[str]) -> list[str]:
        """Buang entri kosong; entri tanpa isi bukan rujukan yang bermakna."""
        return [item for item in value if item]


class RPSSubCourseOutcome(RPSStructuredModel):
    """Sub-CPMK — turunan CPMK yang menjadi sasaran tiap minggu."""

    id: str | None = None
    description: str = Field(min_length=1)
    cpmk_ids: list[str] = Field(default_factory=list)

    @field_validator("cpmk_ids", mode="after")
    @classmethod
    def _drop_blank_entries(cls, value: list[str]) -> list[str]:
        """Buang entri kosong (lihat :meth:`RPSCourseOutcome._drop_blank_entries`)."""
        return [item for item in value if item]


class RPSTopic(RPSStructuredModel):
    """Topik/bahan kajian yang dideklarasikan RPS."""

    id: str | None = None
    name: str = Field(min_length=1)


class RPSMedia(RPSStructuredModel):
    """Media pembelajaran yang disebut RPS (mis. slide, video, LMS, alat peraga)."""

    id: str | None = None
    name: str = Field(min_length=1)
    type: str | None = None
    description: str | None = None


class RPSWeekAssessment(RPSStructuredModel):
    """Assessment satu minggu (content-schema §6.2 ``assessment``).

    Tidak diisi bila RPS tidak menentukan assessment untuk minggu tersebut —
    sistem tidak boleh mengarang assessment (§6.1).
    """

    type: str | None = None
    description: str | None = None
    weight_percent: float | None = Field(default=None, ge=0, le=100)


class RPSWeek(RPSStructuredModel):
    """Distribusi materi per minggu (content-schema §6.2).

    ``topics`` dan ``media`` berisi **nama** yang dideklarasikan pada dokumen,
    sedangkan ``cpmk`` dan ``sub_cpmk`` berisi **kode** (``CPMK-1``, ``SUB-1``)
    yang merujuk entri pada :class:`RPSStructuredData`.
    """

    week: int = Field(ge=1)
    week_type: RPSWeekType = RPSWeekType.REGULAR
    topics: list[str] = Field(default_factory=list)
    cpmk: list[str] = Field(default_factory=list)
    sub_cpmk: list[str] = Field(default_factory=list)
    # Nama field mengikuti content-schema §6.1 (``teaching_method``, tunggal).
    teaching_method: list[str] = Field(default_factory=list)
    media: list[str] = Field(default_factory=list)
    assessment: RPSWeekAssessment | None = None

    @field_validator(
        "topics", "cpmk", "sub_cpmk", "teaching_method", "media", mode="after"
    )
    @classmethod
    def _drop_blank_entries(cls, value: list[str]) -> list[str]:
        """Buang entri kosong; entri tanpa isi bukan informasi akademik."""
        return [item for item in value if item]


class RPSAssessment(RPSStructuredModel):
    """Assessment tingkat mata kuliah (content-schema §6.1 ``assessments``).

    ``weight_percent`` adalah bobot dalam persen bila RPS menyebutkannya; tidak
    diisi bila tidak ada, dan tidak pernah dikira-kira.
    """

    id: str | None = None
    type: str | None = None
    description: str | None = None
    week: int | None = Field(default=None, ge=1)
    weight_percent: float | None = Field(default=None, ge=0, le=100)


class RPSReference(RPSStructuredModel):
    """Satu entri daftar pustaka/referensi (content-schema §6.1 ``references``)."""

    id: str | None = None
    citation: str = Field(min_length=1)
    authors: str | None = None
    year: int | None = None
    source: str | None = None


class RPSExtractionMetadata(RPSStructuredModel):
    """Keterangan tentang proses ekstraksi yang menghasilkan dokumen ini.

    Berbeda dari metadata persistence (§5) yang dimiliki database: object ini
    mencatat **bagaimana** data diperoleh — pipeline/konverter, model bahasa yang
    dipakai, halaman sumber, dan tingkat keyakinan — sehingga hasil ekstraksi
    dapat dievaluasi dan ditelusuri (§3.3).
    """

    extracted_at: datetime | None = None
    extractor: str | None = None
    extractor_version: str | None = None
    model_name: str | None = None
    model_provider: str | None = None
    source_pages: list[int] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("source_pages", mode="after")
    @classmethod
    def _require_positive_pages(cls, value: list[int]) -> list[int]:
        """Nomor halaman mengikuti penomoran dokumen (mulai dari 1)."""
        invalid = sorted(page for page in value if page < 1)
        if invalid:
            raise ValueError(f"nomor halaman harus >= 1, ditemukan: {invalid}")
        return value

    @field_validator("warnings", mode="after")
    @classmethod
    def _drop_blank_entries(cls, value: list[str]) -> list[str]:
        """Buang peringatan kosong (lihat :meth:`RPSWeek._drop_blank_entries`)."""
        return [item for item in value if item]


class DanglingReference(RPSStructuredModel):
    """Rujukan yang tidak menemukan sasaran deklarasinya.

    Dilaporkan sebagai temuan (bukan error) oleh
    :meth:`RPSStructuredData.validate_references`, karena RPS yang berbeda
    memang boleh merujuk kode yang tidak dideklarasikan secara eksplisit.
    """

    #: Asal rujukan: ``week``, ``cpmk``, atau ``sub_cpmk``.
    source: str
    #: Nama field yang memuat rujukan (mis. ``cpl_ids``, ``sub_cpmk``).
    field: str
    value: str
    #: Nomor minggu; hanya terisi bila rujukannya berasal dari sebuah minggu.
    week: int | None = None


class RPSStructuredData(RPSStructuredModel):
    """RPS Structured Data — kontrak lengkap hasil ekstraksi satu dokumen RPS.

    Seluruh field bersifat opsional dan boleh kosong; yang dijaga adalah
    konsistensi internal (nomor minggu tidak boleh duplikat) dan keutuhan entri.
    """

    schema_version: str = Field(default=RPS_SCHEMA_VERSION, min_length=1)
    course: RPSCourseIdentity = Field(default_factory=RPSCourseIdentity)
    cpl: list[RPSGraduateOutcome] = Field(default_factory=list)
    cpmk: list[RPSCourseOutcome] = Field(default_factory=list)
    sub_cpmk: list[RPSSubCourseOutcome] = Field(default_factory=list)
    topics: list[RPSTopic] = Field(default_factory=list)
    weeks: list[RPSWeek] = Field(default_factory=list)
    teaching_methods: list[str] = Field(default_factory=list)
    media: list[RPSMedia] = Field(default_factory=list)
    assessments: list[RPSAssessment] = Field(default_factory=list)
    references: list[RPSReference] = Field(default_factory=list)
    extraction: RPSExtractionMetadata | None = None

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

        ``field`` adalah nama koleksi tingkat dokumen: ``cpl``, ``cpmk``,
        ``sub_cpmk``, atau ``topics``. Entri tanpa ``id`` tidak menghasilkan kode
        apa pun, sehingga tidak dapat dirujuk lewat kode.
        """
        collection = getattr(self, field)
        return {entry.id for entry in collection if entry.id}

    def validate_references(self) -> list[DanglingReference]:
        """Temukan rujukan yang tidak menemukan sasaran (§3.3).

        Traceability RPS mengharuskan setiap rencana mingguan dapat dikaitkan
        dengan sumber akademiknya, dan hierarki capaian pembelajaran harus utuh:
        Sub-CPMK → CPMK → CPL. Pemeriksaan ini **tidak** melempar error: RPS yang
        berbeda boleh menyebut kode yang tidak dideklarasikan pada daftar
        utamanya, dan temuan ini dipakai sebagai bahan validasi (BE-09), bukan
        penghalang pemrosesan.
        """
        cpl_ids = self.declared_ids("cpl")
        cpmk_ids = self.declared_ids("cpmk")
        sub_cpmk_ids = self.declared_ids("sub_cpmk")
        topic_names = {topic.name for topic in self.topics}
        media_names = {media.name for media in self.media}

        findings = _dangling(
            source="cpmk",
            field="cpl_ids",
            values=_referenced(self.cpmk, "cpl_ids"),
            declared=cpl_ids,
        )
        findings += _dangling(
            source="sub_cpmk",
            field="cpmk_ids",
            values=_referenced(self.sub_cpmk, "cpmk_ids"),
            declared=cpmk_ids,
        )

        # Rujukan per minggu: `cpmk`/`sub_cpmk` berisi kode, sedangkan `topics`
        # dan `media` berisi nama yang dideklarasikan (content-schema §6.2),
        # sehingga sasaran pembandingnya berbeda per field.
        weekly_targets: tuple[tuple[str, set[str]], ...] = (
            ("cpmk", cpmk_ids),
            ("sub_cpmk", sub_cpmk_ids),
            ("topics", topic_names),
            ("media", media_names),
        )
        for week in self.weeks:
            for field, declared in weekly_targets:
                findings += _dangling(
                    source="week",
                    field=field,
                    values=list(getattr(week, field)),
                    declared=declared,
                    week=week.week,
                )

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
                self.cpl,
                self.cpmk,
                self.sub_cpmk,
                self.topics,
                self.weeks,
                self.teaching_methods,
                self.media,
                self.assessments,
                self.references,
            )
        )


def _referenced(entries: list[Any], field: str) -> list[str]:
    """Seluruh nilai rujukan pada satu field dari sekumpulan entri."""
    return [value for entry in entries for value in getattr(entry, field)]


def _dangling(
    *,
    source: str,
    field: str,
    values: list[str],
    declared: set[str],
    week: int | None = None,
) -> list[DanglingReference]:
    """Rujukan yang tidak ada pada koleksi sasarannya.

    Koleksi sasaran yang kosong berarti tidak ada yang bisa dirujuk; melaporkan
    seluruh rujukan sebagai temuan hanya akan menghasilkan derau, bukan sinyal
    traceability — karena itu kasus tersebut dilewati.
    """
    if not declared:
        return []
    return [
        DanglingReference(source=source, field=field, value=value, week=week)
        for value in values
        if value not in declared
    ]


def to_rps_analysis_payload(data: RPSStructuredData) -> dict[str, Any]:
    """Petakan RPS Structured Data ke kolom tabel ``rps_analyses``.

    Bentuk kolom mengikuti ``docs/02. design/data-model.md`` §9 dan
    ``src/models/rps_analysis.py``:

    - ``learning_outcomes`` ← ``cpmk`` (CPMK adalah capaian pembelajaran **mata
      kuliah**, padanan terdekat dari kolom tersebut);
    - ``objectives`` ← ``sub_cpmk`` (sasaran yang lebih rinci);
    - ``raw_analysis`` ← seluruh dokumen, sehingga CPL, media, dan metadata
      ekstraksi yang belum punya kolom tersendiri tetap tersimpan utuh dan dapat
      diangkat menjadi kolom bila BE-08 membutuhkannya.

    Kolom ``references`` pada database direpresentasikan sebagai
    ``references_data`` pada model ORM (nama ``references`` dipakai SQLAlchemy
    untuk terminologi relasi).

    Payload yang dikembalikan siap dipakai sebagai argumen kata kunci
    ``RPSAnalysis(...)``, sehingga BE-08 tidak perlu memetakan ulang:

    ```python
    payload = to_rps_analysis_payload(extracted)
    analysis = RPSAnalysis(rps_id=rps_id, version=1, **payload)
    ```
    """
    return {
        "course_identity": data.course.model_dump(mode="json"),
        "learning_outcomes": [entry.model_dump(mode="json") for entry in data.cpmk],
        "objectives": [entry.model_dump(mode="json") for entry in data.sub_cpmk],
        "topics": [entry.model_dump(mode="json") for entry in data.topics],
        "weekly_distribution": [week.model_dump(mode="json") for week in data.weeks],
        "teaching_methods": list(data.teaching_methods),
        "assessments": [entry.model_dump(mode="json") for entry in data.assessments],
        "references_data": [entry.model_dump(mode="json") for entry in data.references],
        "raw_analysis": data.model_dump(mode="json"),
    }
