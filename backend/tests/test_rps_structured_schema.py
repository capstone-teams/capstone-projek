"""Test RPS Structured Data Schema (BE-05.3).

Schema ini adalah kontrak antara backend dan AI, sehingga yang diuji di sini
adalah **janji kontraknya**, bukan sekadar parsing JSON:

- hierarki capaian pembelajaran CPL → CPMK → Sub-CPMK beserta rujukan silangnya;
- bentuk object dan nama field sesuai content-schema §6.1/§6.2;
- field yang tidak tersedia boleh kosong, dan nilai kosong tidak berubah menjadi
  data palsu (§6: sistem tidak boleh mengarang);
- aturan validasi yang diminta issue #99: minggu bilangan bulat positif,
  ``week_type`` bernilai ``regular``/``uts``/``uas``, ``weight_percent`` pada
  rentang 0–100;
- field di luar kontrak ditolak (§3.2/§3.4), bukan dibuang diam-diam;
- pemetaan ke tabel ``rps_analyses`` benar-benar cocok dengan kolom yang ada di
  model ORM (data-model §9) — inilah yang dipakai BE-08.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from src.models.rps_analysis import RPSAnalysis
from src.schemas.rps_structured import (
    RPS_SCHEMA_VERSION,
    DanglingReference,
    RPSAssessment,
    RPSCourseIdentity,
    RPSCourseOutcome,
    RPSExtractionMetadata,
    RPSGraduateOutcome,
    RPSMedia,
    RPSReference,
    RPSStructuredData,
    RPSSubCourseOutcome,
    RPSTopic,
    RPSWeek,
    RPSWeekAssessment,
    RPSWeekType,
    to_rps_analysis_payload,
)

EXAMPLE_RPS = {
    "course": {
        "name": "Matematika Diskrit",
        "code": "IF234",
        "credits": 3,
        "semester": 3,
        "description": "Mata kuliah dasar matematika diskrit.",
    },
    "cpl": [{"id": "CPL-1", "description": "Menerapkan matematika, statistika, dan struktur diskrit"}],
    "cpmk": [
        {
            "id": "CPMK-1",
            "description": "Menerapkan konsep matematika diskrit",
            "cpl_ids": ["CPL-1"],
        }
    ],
    "sub_cpmk": [
        {
            "id": "SUB-1",
            "description": "Menjelaskan kombinatorial dan peluang diskrit",
            "cpmk_ids": ["CPMK-1"],
        }
    ],
    "topics": [{"id": "TOP-1", "name": "Kombinatorial"}],
    "media": [{"name": "Slide presentasi", "type": "presentation"}],
    "weeks": [
        {
            "week": 1,
            "week_type": "regular",
            "topics": ["Kombinatorial"],
            "cpmk": ["CPMK-1"],
            "sub_cpmk": ["SUB-1"],
            "teaching_method": ["Lecture"],
            "media": ["Slide presentasi"],
            "assessment": {"type": "assignment", "description": "Latihan kombinatorial"},
        },
        {"week": 8, "week_type": "uts"},
        {"week": 16, "week_type": "uas"},
    ],
    "teaching_methods": ["Lecture", "Lab"],
    "assessments": [
        {"id": "A-1", "type": "assignment", "week": 1, "weight_percent": 3.75}
    ],
    "references": [{"id": "R-1", "citation": "Rosen, Discrete Mathematics"}],
    "extraction": {
        "extracted_at": "2026-10-16T13:30:31+00:00",
        "extractor": "docling",
        "extractor_version": "2.140.0",
        "model_name": "gpt-4o-mini",
        "model_provider": "openai",
        "source_pages": [1, 2],
        "confidence": 0.86,
        "warnings": ["tabel halaman 2 tidak lengkap"],
    },
}


def test_default_schema_version_is_the_current_contract_version():
    assert RPSStructuredData().schema_version == RPS_SCHEMA_VERSION


def test_the_contract_version_is_the_explicit_hierarchy_revision():
    """Versi 2.0 menandai perubahan breaking: hierarki capaian pembelajaran."""
    assert RPS_SCHEMA_VERSION == "2.0"


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_schema_version_falls_back_to_the_current_version(blank):
    """Versi kosong berarti "tidak disebutkan", bukan versi kosong yang tak berarti."""
    data = RPSStructuredData.model_validate({"schema_version": blank})

    assert data.schema_version == RPS_SCHEMA_VERSION


def test_an_empty_document_is_valid_because_not_every_rps_has_every_field():
    """§6: field yang tidak tersedia pada RPS boleh kosong atau null."""
    data = RPSStructuredData()

    assert data.course == RPSCourseIdentity()
    assert data.weeks == []
    assert data.extraction is None
    assert not data.has_academic_content()


def test_the_documented_example_round_trips_through_json():
    """Bentuk pada content-schema §6.1/§6.2 harus dapat dibaca apa adanya."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    restored = RPSStructuredData.model_validate(json.loads(data.model_dump_json()))

    assert restored == data
    assert data.cpl == [
        RPSGraduateOutcome(
            id="CPL-1", description="Menerapkan matematika, statistika, dan struktur diskrit"
        )
    ]
    assert data.cpmk == [
        RPSCourseOutcome(
            id="CPMK-1",
            description="Menerapkan konsep matematika diskrit",
            cpl_ids=["CPL-1"],
        )
    ]
    assert data.sub_cpmk == [
        RPSSubCourseOutcome(
            id="SUB-1",
            description="Menjelaskan kombinatorial dan peluang diskrit",
            cpmk_ids=["CPMK-1"],
        )
    ]
    assert data.media == [
        RPSMedia(id=None, name="Slide presentasi", type="presentation", description=None)
    ]
    assert data.assessments == [
        RPSAssessment(
            id="A-1",
            type="assignment",
            description=None,
            week=1,
            weight_percent=3.75,
        )
    ]
    assert data.references == [
        RPSReference(
            id="R-1",
            citation="Rosen, Discrete Mathematics",
            authors=None,
            year=None,
            source=None,
        )
    ]


def test_week_schema_matches_the_documented_fields():
    """§6.2: ``teaching_method`` (tunggal), ``week_type``, dan rujukan berkode."""
    week = RPSWeek.model_validate(
        {
            "week": 2,
            "week_type": "regular",
            "topics": ["Graf"],
            "cpmk": ["CPMK-1"],
            "sub_cpmk": ["SUB-1"],
            "teaching_method": ["Lecture"],
            "media": ["Slide presentasi"],
            "assessment": {"type": "quiz", "description": "Kuis singkat", "weight_percent": 10},
        }
    )

    assert week.week_type is RPSWeekType.REGULAR
    assert week.teaching_method == ["Lecture"]
    assert week.media == ["Slide presentasi"]
    assert week.assessment == RPSWeekAssessment(
        type="quiz", description="Kuis singkat", weight_percent=10
    )


@pytest.mark.parametrize("week_type", ["regular", "uts", "uas"])
def test_all_documented_week_types_are_accepted(week_type):
    assert RPSWeek.model_validate({"week": 1, "week_type": week_type}).week_type.value == week_type


def test_an_unknown_week_type_is_rejected():
    with pytest.raises(ValidationError):
        RPSWeek.model_validate({"week": 1, "week_type": "libur"})


def test_a_week_defaults_to_a_regular_week():
    """RPS yang tidak menandai minggu ujian tetap terbaca sebagai minggu biasa."""
    assert RPSWeek.model_validate({"week": 3}).week_type is RPSWeekType.REGULAR


@pytest.mark.parametrize("weight", [0, 3.75, 100])
def test_weight_percent_accepts_the_documented_range(weight):
    assert RPSAssessment.model_validate({"weight_percent": weight}).weight_percent == weight


@pytest.mark.parametrize("weight", [-1, 100.5, 250])
def test_weight_percent_outside_zero_to_hundred_is_rejected(weight):
    with pytest.raises(ValidationError):
        RPSAssessment.model_validate({"weight_percent": weight})

    with pytest.raises(ValidationError):
        RPSWeekAssessment.model_validate({"weight_percent": weight})


def test_extraction_metadata_records_how_the_data_was_obtained():
    extraction = RPSStructuredData.model_validate(EXAMPLE_RPS).extraction

    assert extraction == RPSExtractionMetadata(
        extracted_at="2026-10-16T13:30:31+00:00",
        extractor="docling",
        extractor_version="2.140.0",
        model_name="gpt-4o-mini",
        model_provider="openai",
        source_pages=[1, 2],
        confidence=0.86,
        warnings=["tabel halaman 2 tidak lengkap"],
    )


@pytest.mark.parametrize("pages", [[0], [-1, 2]])
def test_extraction_source_pages_are_document_page_numbers(pages):
    """Penomoran halaman dokumen dimulai dari 1."""
    with pytest.raises(ValidationError):
        RPSExtractionMetadata.model_validate({"source_pages": pages})


@pytest.mark.parametrize("confidence", [-0.1, 1.5])
def test_extraction_confidence_is_a_ratio(confidence):
    with pytest.raises(ValidationError):
        RPSExtractionMetadata.model_validate({"confidence": confidence})


def test_unknown_fields_are_rejected_instead_of_silently_dropped():
    """§3.2/§3.4: schema adalah kontrak, bukan wadah serbaguna."""
    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate({"course": {"name": "Matdis", "unknown": 1}})

    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate({"additional_data": {"apa pun": True}})

    # Bentuk lama (v1.0) tidak lagi diterima: field-nya sudah digantikan
    # hierarki CPL/CPMK/Sub-CPMK, dan schema menolaknya secara eksplisit.
    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate(
            {"learning_outcomes": [{"id": "LO-1", "description": "x"}]}
        )


@pytest.mark.parametrize(
    "entry",
    [
        {"cpl": [{"id": "CPL-1"}]},
        {"cpmk": [{"id": "CPMK-1"}]},
        {"sub_cpmk": [{"id": "SUB-1"}]},
        {"topics": [{"id": "TOP-1"}]},
        {"media": [{"id": "M-1"}]},
        {"references": [{"id": "R-1"}]},
    ],
)
def test_an_entry_must_have_substance_not_just_an_identifier(entry):
    """Entri tanpa isi akademik tidak boleh lolos hanya karena punya kode."""
    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate(entry)


def test_blank_values_are_treated_as_absent_not_as_content():
    """Model bahasa sering mengisi field yang tidak ditemukan dengan string kosong."""
    data = RPSStructuredData.model_validate(
        {
            "course": {"name": "  ", "code": "", "description": None},
            "weeks": [
                {
                    "week": 1,
                    "topics": ["Graf", ""],
                    "teaching_method": ["", "Lab"],
                    "cpmk": ["", "CPMK-1"],
                }
            ],
            "teaching_methods": ["", "Lecture"],
            "media": [{"name": "Slide", "type": ""}],
        }
    )

    assert data.course.name is None
    assert data.course.code is None
    assert data.weeks[0].topics == ["Graf"]
    assert data.weeks[0].teaching_method == ["Lab"]
    assert data.weeks[0].cpmk == ["CPMK-1"]
    assert data.teaching_methods == ["Lecture"]
    assert data.media[0].type is None


def test_duplicate_week_numbers_are_rejected():
    """Dua entri untuk minggu yang sama membuat distribusi materi ambigu."""
    with pytest.raises(ValidationError) as excinfo:
        RPSStructuredData.model_validate({"weeks": [{"week": 3}, {"week": 1}, {"week": 3}]})

    assert "duplikat" in str(excinfo.value)


@pytest.mark.parametrize("week", [0, -1])
def test_week_numbers_must_be_positive(week):
    with pytest.raises(ValidationError):
        RPSWeek.model_validate({"week": week})


def test_a_complete_hierarchy_has_no_reference_findings():
    """§3.3: Sub-CPMK → CPMK → CPL dan rujukan mingguan harus utuh."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    assert data.validate_references() == []


def test_dangling_references_are_reported_across_the_whole_hierarchy():
    """Temuan dilaporkan, bukan dilempar sebagai error."""
    data = RPSStructuredData.model_validate(
        {
            "cpl": [{"id": "CPL-1", "description": "a"}],
            "cpmk": [{"id": "CPMK-1", "description": "b", "cpl_ids": ["CPL-1", "CPL-9"]}],
            "sub_cpmk": [{"id": "SUB-1", "description": "c", "cpmk_ids": ["CPMK-9"]}],
            "topics": [{"name": "Graf"}],
            "media": [{"name": "Slide"}],
            "weeks": [
                {
                    "week": 5,
                    "cpmk": ["CPMK-1", "CPMK-8"],
                    "sub_cpmk": ["SUB-9"],
                    "topics": ["Graf", "Topik Tak Dikenal"],
                    "media": ["Slide", "Video Tak Dikenal"],
                }
            ],
        }
    )

    findings = {
        (finding.source, finding.field, finding.value, finding.week)
        for finding in data.validate_references()
    }

    assert findings == {
        ("cpmk", "cpl_ids", "CPL-9", None),
        ("sub_cpmk", "cpmk_ids", "CPMK-9", None),
        ("week", "cpmk", "CPMK-8", 5),
        ("week", "sub_cpmk", "SUB-9", 5),
        ("week", "topics", "Topik Tak Dikenal", 5),
        ("week", "media", "Video Tak Dikenal", 5),
    }


def test_references_are_not_reported_when_there_is_nothing_to_reference():
    """Koleksi sasaran kosong bukan pelanggaran traceability, hanya tidak ada acuan."""
    data = RPSStructuredData.model_validate(
        {
            "weeks": [
                {
                    "week": 1,
                    "cpmk": ["CPMK-1"],
                    "sub_cpmk": ["SUB-1"],
                    "topics": ["Apa saja"],
                    "media": ["Apa saja"],
                }
            ]
        }
    )

    assert data.validate_references() == []


def test_has_academic_content_detects_an_empty_extraction():
    assert not RPSStructuredData().has_academic_content()
    assert RPSStructuredData(course=RPSCourseIdentity(name="Matdis")).has_academic_content()
    assert RPSStructuredData(topics=[RPSTopic(name="Graf")]).has_academic_content()
    assert RPSStructuredData(
        cpl=[RPSGraduateOutcome(description="Menerapkan matematika")]
    ).has_academic_content()
    assert RPSStructuredData(
        media=[RPSMedia(name="Slide")]
    ).has_academic_content()


def test_payload_can_be_splatted_into_the_rps_analyses_entity():
    """Kontrak BE-08: payload harus langsung dapat menjadi kolom ``rps_analyses``.

    Diuji dengan benar-benar membangun entity ORM-nya: nama pada payload harus
    sama dengan nama atribut mapped (termasuk ``references_data``, yang kolom
    database-nya bernama ``references``). Salah nama berarti BE-08 akan gagal
    saat menulis analisis.
    """
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    analysis = RPSAnalysis(rps_id="a" * 22, version=1, **to_rps_analysis_payload(data))

    # CPMK ↔ kolom `learning_outcomes`, Sub-CPMK ↔ kolom `objectives` (data-model §9).
    assert analysis.learning_outcomes == [
        {
            "id": "CPMK-1",
            "description": "Menerapkan konsep matematika diskrit",
            "cpl_ids": ["CPL-1"],
        }
    ]
    assert analysis.objectives == [
        {
            "id": "SUB-1",
            "description": "Menjelaskan kombinatorial dan peluang diskrit",
            "cpmk_ids": ["CPMK-1"],
        }
    ]
    assert analysis.weekly_distribution[0]["week"] == 1
    assert analysis.references_data[0]["citation"].startswith("Rosen")
    assert analysis.raw_analysis["schema_version"] == RPS_SCHEMA_VERSION


def test_payload_keeps_what_has_no_column_of_its_own_in_raw_analysis():
    """CPL, media, dan metadata ekstraksi belum punya kolom; tidak boleh hilang."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    raw = to_rps_analysis_payload(data)["raw_analysis"]

    assert raw["cpl"][0]["id"] == "CPL-1"
    assert raw["media"][0]["name"] == "Slide presentasi"
    assert raw["extraction"]["extractor"] == "docling"
    assert raw["weeks"][1] == {
        "week": 8,
        "week_type": "uts",
        "topics": [],
        "cpmk": [],
        "sub_cpmk": [],
        "teaching_method": [],
        "media": [],
        "assessment": None,
    }


def test_dangling_reference_is_a_serializable_contract_object():
    """Temuan dipakai sebagai bahan validasi (BE-09), jadi harus dapat disimpan."""
    finding = DanglingReference(source="week", field="sub_cpmk", value="SUB-9", week=4)

    assert json.loads(finding.model_dump_json()) == {
        "source": "week",
        "field": "sub_cpmk",
        "value": "SUB-9",
        "week": 4,
    }


def test_json_schema_is_publishable_for_the_ai_team():
    """Kontrak harus dapat dibagikan sebagai JSON Schema (content-schema §45)."""
    schema = RPSStructuredData.model_json_schema()

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {
        "schema_version",
        "course",
        "cpl",
        "cpmk",
        "sub_cpmk",
        "topics",
        "weeks",
        "teaching_methods",
        "media",
        "assessments",
        "references",
        "extraction",
    }
    assert schema["additionalProperties"] is False
    assert "$defs" in schema and "RPSWeekType" in schema["$defs"]
