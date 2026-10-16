"""Test RPS Structured Data Schema (BE-05.3).

Schema ini adalah kontrak antara backend dan AI, sehingga yang diuji di sini
adalah **janji kontraknya**, bukan sekadar parsing JSON:

- bentuk object dan nama field sesuai content-schema §6/§7;
- field yang tidak tersedia boleh kosong, dan nilai kosong tidak berubah menjadi
  data palsu (§6: sistem tidak boleh mengarang);
- field di luar kontrak ditolak (§3.2/§3.4), bukan dibuang diam-diam;
- konsistensi internal (nomor minggu unik) dan traceability (§3.3) dapat
  diperiksa;
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
    RPSAssessment,
    RPSCourseIdentity,
    RPSLearningOutcome,
    RPSObjective,
    RPSReference,
    RPSStructuredData,
    RPSTopic,
    RPSWeek,
    RPSWeekAssessment,
    to_rps_analysis_payload,
)

EXAMPLE_RPS = {
    "course": {
        "name": "Basis Data",
        "code": "IF123",
        "credits": 3,
        "semester": 3,
        "description": "Mata kuliah dasar basis data.",
    },
    "learning_outcomes": [{"id": "LO-1", "description": "Mampu merancang skema relasional"}],
    "objectives": [{"id": "OBJ-1", "description": "Menjelaskan normalisasi"}],
    "topics": [{"id": "TOP-1", "name": "Database Fundamentals"}],
    "weeks": [
        {
            "week": 1,
            "topics": ["Database Fundamentals"],
            "learning_outcomes": ["LO-1"],
            "objectives": ["OBJ-1"],
            "teaching_method": ["Lecture"],
            "assessment": {"type": "assignment", "description": "Membuat ERD"},
        }
    ],
    "teaching_methods": ["Lecture", "Lab"],
    "assessments": [{"id": "A-1", "type": "assignment", "week": 1, "weight": 20}],
    "references": [{"id": "R-1", "citation": "Silberschatz, Database System Concepts"}],
}


def test_default_schema_version_is_the_current_contract_version():
    assert RPSStructuredData().schema_version == RPS_SCHEMA_VERSION


@pytest.mark.parametrize("blank", ["", "   ", None])
def test_blank_schema_version_falls_back_to_the_current_version(blank):
    """Versi kosong berarti "tidak disebutkan", bukan versi kosong yang tak berarti."""
    data = RPSStructuredData.model_validate({"schema_version": blank})

    assert data.schema_version == RPS_SCHEMA_VERSION


def test_an_empty_document_is_valid_because_not_every_rps_has_every_field():
    """§6/§7: field yang tidak tersedia pada RPS boleh kosong atau null."""
    data = RPSStructuredData()

    assert data.course == RPSCourseIdentity()
    assert data.weeks == []
    assert not data.has_academic_content()


def test_the_documented_example_round_trips_through_json():
    """Bentuk pada content-schema §6/§7 harus dapat dibaca apa adanya."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    restored = RPSStructuredData.model_validate(json.loads(data.model_dump_json()))

    assert restored == data
    assert data.course == RPSCourseIdentity(
        name="Basis Data",
        code="IF123",
        credits=3,
        semester=3,
        description="Mata kuliah dasar basis data.",
    )
    assert data.learning_outcomes == [
        RPSLearningOutcome(id="LO-1", description="Mampu merancang skema relasional")
    ]
    assert data.topics == [RPSTopic(id="TOP-1", name="Database Fundamentals")]
    assert data.weeks[0].assessment == RPSWeekAssessment(
        type="assignment", description="Membuat ERD"
    )
    assert data.assessments == [
        RPSAssessment(id="A-1", type="assignment", description=None, week=1, weight=20)
    ]
    assert data.references == [
        RPSReference(
            id="R-1",
            citation="Silberschatz, Database System Concepts",
            authors=None,
            year=None,
            source=None,
        )
    ]


def test_field_names_match_the_documented_week_schema():
    """§7 memakai ``teaching_method`` (tunggal) dan ``topics`` berisi nama topik."""
    week = RPSWeek.model_validate(
        {
            "week": 2,
            "topics": ["Normalisasi"],
            "learning_outcomes": ["LO-1"],
            "objectives": ["OBJ-1"],
            "teaching_method": ["Lecture"],
            "assessment": {"type": "quiz", "description": "Kuis singkat"},
        }
    )

    assert week.teaching_method == ["Lecture"]
    assert week.topics == ["Normalisasi"]
    assert week.assessment is not None and week.assessment.type == "quiz"


def test_unknown_fields_are_rejected_instead_of_silently_dropped():
    """§3.2/§3.4: schema adalah kontrak, bukan wadah serbaguna."""
    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate({"course": {"name": "Basis Data", "unknown": 1}})

    with pytest.raises(ValidationError):
        RPSStructuredData.model_validate({"additional_data": {"apa pun": True}})


@pytest.mark.parametrize(
    "entry",
    [
        {"learning_outcomes": [{"id": "LO-1"}]},
        {"objectives": [{"id": "OBJ-1"}]},
        {"topics": [{"id": "TOP-1"}]},
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
            "weeks": [{"week": 1, "topics": ["Normalisasi", ""], "teaching_method": ["", "Lab"]}],
            "teaching_methods": ["", "Lecture"],
        }
    )

    assert data.course.name is None
    assert data.course.code is None
    assert data.weeks[0].topics == ["Normalisasi"]
    assert data.weeks[0].teaching_method == ["Lab"]
    assert data.teaching_methods == ["Lecture"]


def test_duplicate_week_numbers_are_rejected():
    """Dua entri untuk minggu yang sama membuat distribusi materi ambigu."""
    with pytest.raises(ValidationError) as excinfo:
        RPSStructuredData.model_validate({"weeks": [{"week": 3}, {"week": 1}, {"week": 3}]})

    assert "duplikat" in str(excinfo.value)


def test_week_numbers_must_be_positive():
    with pytest.raises(ValidationError):
        RPSWeek.model_validate({"week": 0})


def test_references_to_declared_ids_are_traceable():
    """§3.3: rencana mingguan harus dapat dikaitkan ke LO/Objective/Topic sumbernya."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    assert data.validate_references() == []


def test_dangling_references_are_reported_without_failing_the_document():
    data = RPSStructuredData.model_validate(
        {
            "learning_outcomes": [{"id": "LO-1", "description": "Capaian satu"}],
            "topics": [{"name": "Normalisasi"}],
            "weeks": [
                {
                    "week": 1,
                    "learning_outcomes": ["LO-1", "LO-9"],
                    "topics": ["Normalisasi", "Topik Tak Dikenal"],
                }
            ],
        }
    )

    findings = {(finding.field, finding.value) for finding in data.validate_references()}

    assert findings == {("learning_outcomes", "LO-9"), ("topics", "Topik Tak Dikenal")}


def test_references_are_not_reported_when_there_is_nothing_to_reference():
    """Koleksi sasaran kosong bukan pelanggaran traceability, hanya tidak ada acuan."""
    data = RPSStructuredData.model_validate(
        {"weeks": [{"week": 1, "learning_outcomes": ["LO-1"], "topics": ["Apa saja"]}]}
    )

    assert data.validate_references() == []


def test_has_academic_content_detects_an_empty_extraction():
    assert not RPSStructuredData().has_academic_content()
    assert RPSStructuredData(course=RPSCourseIdentity(name="Basis Data")).has_academic_content()
    assert RPSStructuredData(topics=[RPSTopic(name="Normalisasi")]).has_academic_content()
    assert RPSStructuredData(
        objectives=[RPSObjective(description="Menjelaskan normalisasi")]
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

    assert analysis.course_identity["code"] == "IF123"
    assert analysis.weekly_distribution[0]["week"] == 1
    assert analysis.references_data[0]["citation"].startswith("Silberschatz")
    assert analysis.raw_analysis["schema_version"] == RPS_SCHEMA_VERSION
    assert analysis.learning_outcomes == [
        {"id": "LO-1", "description": "Mampu merancang skema relasional"}
    ]


def test_payload_uses_the_column_name_for_references():
    """Kolom ``references`` pada tabel dipetakan sebagai ``references_data`` di ORM."""
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    payload = to_rps_analysis_payload(data)

    assert payload["references_data"] == [
        {
            "id": "R-1",
            "citation": "Silberschatz, Database System Concepts",
            "authors": None,
            "year": None,
            "source": None,
        }
    ]
    assert "references" not in payload


def test_payload_keeps_the_complete_analysis_for_traceability():
    data = RPSStructuredData.model_validate(EXAMPLE_RPS)

    payload = to_rps_analysis_payload(data)

    assert payload["raw_analysis"]["schema_version"] == RPS_SCHEMA_VERSION
    assert payload["raw_analysis"]["course"]["code"] == "IF123"
    assert payload["weekly_distribution"][0]["week"] == 1
    assert payload["course_identity"]["name"] == "Basis Data"
    assert payload["teaching_methods"] == ["Lecture", "Lab"]


def test_json_schema_is_publishable_for_the_ai_team():
    """Kontrak harus dapat dibagikan sebagai JSON Schema (content-schema §45)."""
    schema = RPSStructuredData.model_json_schema()

    assert schema["type"] == "object"
    assert set(schema["properties"]) == {
        "schema_version",
        "course",
        "learning_outcomes",
        "objectives",
        "topics",
        "weeks",
        "teaching_methods",
        "assessments",
        "references",
    }
    assert schema["additionalProperties"] is False
