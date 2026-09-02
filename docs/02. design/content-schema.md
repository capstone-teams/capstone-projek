# Content Schema

## 1. Document Information

| Item              | Value                                                                   |
| ----------------- | ----------------------------------------------------------------------- |
| Document          | Content Schema                                                          |
| Project           | Agentic AI untuk Mengisi Konten Moodle                                  |
| Status            | Proposed                                                                |
| Owner             | Capstone Team                                                           |
| Related Documents | PRD, System Design, Data Model, Agent Design, Moodle Integration Design |
| Representation    | Structured JSON + Markdown                                              |
| Validation        | Schema Validation + Semantic Validation                                 |

---

# 2. Purpose

Dokumen ini mendefinisikan struktur data yang digunakan untuk merepresentasikan:

* hasil analisis RPS;
* course plan;
* weekly plan;
* learning material;
* assignment;
* quiz;
* resources;
* validation result;
* Moodle execution payload.

Schema menjadi contract antar-component.

```text
RPS Processing
      ↓
RPS Analysis Schema
      ↓
Course Plan Schema
      ↓
Weekly Content Schema
      ↓
Validation
      ↓
Moodle Mapping
```

---

# 3. Design Principles

## 3.1 Structured First

Data yang diproses antar-component harus menggunakan structured representation.

Markdown digunakan terutama sebagai:

* readable content;
* content authoring representation;
* preview;
* storage representation untuk learning material.

JSON digunakan untuk:

* metadata;
* relationships;
* configuration;
* structured content;
* validation;
* tool input/output.

---

## 3.2 Schema is a Contract

Setiap output agent harus melewati schema validation sebelum:

* disimpan;
* diteruskan ke tahap berikutnya;
* digunakan sebagai tool input;
* dikirim ke Moodle.

---

## 3.3 RPS Traceability

Generated content harus dapat dikaitkan dengan sumber akademiknya.

Minimal setiap weekly plan memiliki reference terhadap:

```text
RPS Analysis
Course Plan
Week
Learning Outcome / Objective
Topic
```

---

## 3.4 Extensible but Controlled

Schema menggunakan field tambahan secara terbatas.

Jangan membuat:

```text
additional_data: arbitrary everything
```

untuk seluruh object.

Field utama harus tetap eksplisit.

---

# 4. Schema Hierarchy

```text
Course
│
├── Course Plan
│    │
│    ├── Week 1
│    │    ├── Learning Material
│    │    ├── Resource
│    │    ├── Assignment (optional)
│    │    └── Quiz (optional)
│    │
│    ├── Week 2
│    │    └── ...
│    │
│    └── Week N
│
└── Activity Configuration
```

---

# 5. Common Metadata

Object yang disimpan sebagai structured JSON dapat memiliki metadata:

```json id="x3u0jk"
{
  "id": "uuid",
  "version": 1,
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

Database tetap menjadi source of truth untuk persistence metadata.

Schema JSON tidak boleh menggantikan relational identity.

---

# 6. RPS Analysis Schema

RPS Analysis merupakan intermediate representation antara document processing dan planning.

```json id="o0s4uw"
{
  "course": {
    "name": "Basis Data",
    "code": "IF123",
    "credits": 3,
    "semester": 3,
    "description": "..."
  },
  "learning_outcomes": [
    {
      "id": "LO-1",
      "description": "..."
    }
  ],
  "objectives": [
    {
      "id": "OBJ-1",
      "description": "..."
    }
  ],
  "topics": [
    {
      "id": "TOP-1",
      "name": "Database Fundamentals"
    }
  ],
  "weeks": [],
  "teaching_methods": [],
  "assessments": [],
  "references": []
}
```

Field yang tidak tersedia pada RPS boleh kosong atau null.

Agent tidak boleh mengisi informasi akademik yang tidak ditemukan hanya untuk membuat schema terlihat lengkap.

---

# 7. RPS Week Schema

```json id="q7w1q4"
{
  "week": 1,
  "topics": [
    "Introduction to Database"
  ],
  "learning_outcomes": [
    "LO-1"
  ],
  "objectives": [
    "OBJ-1"
  ],
  "teaching_method": [
    "Lecture"
  ],
  "assessment": {
    "type": "assignment",
    "description": "..."
  }
}
```

Tidak semua field harus tersedia.

Jika RPS tidak menentukan assessment untuk minggu tertentu, sistem tidak boleh mengarang assessment.

---

# 8. Course Plan Schema

Course Plan merupakan hasil planning agent.

```json id="w5hr8k"
{
  "course": {
    "title": "Basis Data",
    "code": "IF123",
    "description": "..."
  },
  "weeks": [
    {
      "week_number": 1,
      "title": "Introduction to Database",
      "learning_outcomes": [
        "LO-1"
      ],
      "objectives": [
        "OBJ-1"
      ],
      "topics": [
        "Database fundamentals"
      ],
      "teaching_methods": [
        "Lecture"
      ],
      "planned_activities": []
    }
  ]
}
```

---

# 9. Course Plan Week

Minimal structure:

```json id="x1i6hz"
{
  "week_number": 1,
  "title": "Introduction to Database",
  "learning_outcomes": [
    "LO-1"
  ],
  "objectives": [
    "OBJ-1"
  ],
  "topics": [
    "Database fundamentals"
  ],
  "activities": []
}
```

`week_number` harus mengikuti struktur RPS.

---

# 10. Activity Configuration

Instructor menentukan activity yang dihasilkan.

Minimal:

```json id="q2t2zj"
{
  "learning_material": true,
  "assignment": false,
  "quiz": false
}
```

More detailed version:

```json id="y6p6e0"
{
  "learning_material": {
    "enabled": true
  },
  "assignment": {
    "enabled": true,
    "count": 1
  },
  "quiz": {
    "enabled": false,
    "count": 0
  }
}
```

Exact final configuration schema dapat disederhanakan berdasarkan kebutuhan UI MVP.

---

# 11. Learning Material Schema

Learning material merupakan content utama MVP.

```json id="4u6z9k"
{
  "type": "learning_material",
  "title": "Introduction to Database",
  "summary": "...",
  "learning_objectives": [
    "Explain basic database concepts"
  ],
  "sections": [
    {
      "title": "What is a Database?",
      "content": "..."
    },
    {
      "title": "Database Components",
      "content": "..."
    }
  ],
  "examples": [
    {
      "title": "Example Case",
      "description": "..."
    }
  ],
  "references": [
    {
      "title": "Database Systems",
      "url": null
    }
  ]
}
```

`url` bersifat optional.

Sistem tidak boleh mengarang URL referensi.

---

# 12. Learning Material Markdown

Structured learning material dapat dirender menjadi Markdown.

Contoh:

```markdown id="v0mb40"
# Introduction to Database

## Learning Objectives

- Explain basic database concepts.
- Identify major database components.

## What is a Database?

...

## Database Components

...

## Example

...

## References

- Database Systems
```

Markdown merupakan representation untuk readability/rendering.

Structured JSON tetap menjadi source untuk machine processing.

---

# 13. Learning Material Sections

Section digunakan agar content tidak menjadi satu string panjang.

```json id="efq2xw"
{
  "title": "Database Components",
  "content": "...",
  "order": 2
}
```

Minimal:

* title;
* content;
* order.

---

# 14. Resource Schema

Resource digunakan untuk referensi atau supporting material.

```json id="v7s0f5"
{
  "type": "resource",
  "title": "Database Reference",
  "description": "...",
  "resource_type": "external_link",
  "url": "https://example.com"
}
```

Untuk external resources:

* URL harus berasal dari trusted source;
* system tidak boleh membuat URL yang tidak diverifikasi.

Untuk MVP, external resource generation dapat dibuat optional.

---

# 15. Assignment Schema

Assignment hanya dibuat jika enabled.

```json id="f1lyar"
{
  "type": "assignment",
  "title": "Database Design Exercise",
  "description": "...",
  "instructions": [
    "Design an ERD for the given case."
  ],
  "submission_type": [
    "file"
  ],
  "due": null,
  "grading": {
    "max_grade": 100,
    "rubric": []
  }
}
```

Jika due date tidak berasal dari RPS atau instructor configuration:

```text
due = null
```

Agent tidak boleh mengarang deadline.

---

# 16. Assignment Rubric

Optional:

```json id="0q8k3p"
{
  "criterion": "Entity identification",
  "description": "...",
  "weight": 30
}
```

MVP dapat menyimpan rubric sebagai structured data tanpa harus langsung mengimplementasikan advanced Moodle grading/rubric integration.

---

# 17. Quiz Schema

Quiz hanya dibuat jika enabled dan Moodle capability tersedia.

```json id="i2x4el"
{
  "type": "quiz",
  "title": "Database Fundamentals Quiz",
  "description": "...",
  "questions": [
    {
      "type": "multiple_choice",
      "question": "What is a database?",
      "options": [
        {
          "text": "...",
          "correct": true
        },
        {
          "text": "...",
          "correct": false
        }
      ],
      "explanation": "..."
    }
  ]
}
```

---

# 18. Supported Quiz Types

MVP should limit question types.

Recommended initial types:

```text
multiple_choice
true_false
short_answer
```

Additional types:

```text
essay
matching
numerical
```

dapat ditambahkan kemudian.

Jangan memperluas question types sebelum Moodle integration capability terbukti.

---

# 19. Quiz Configuration

```json id="2vhx0v"
{
  "attempts": 1,
  "time_limit_minutes": null,
  "passing_grade": null,
  "randomize_questions": false
}
```

Jika RPS/instructor tidak memberikan nilai konfigurasi:

```text
null
```

lebih aman daripada membuat asumsi akademik.

---

# 20. Weekly Content Schema

Satu minggu dapat memiliki beberapa content/activity.

```json id="8d0v9m"
{
  "week_number": 1,
  "title": "Introduction to Database",
  "learning_objectives": [],
  "items": [
    {
      "type": "learning_material",
      "content_id": "..."
    },
    {
      "type": "assignment",
      "content_id": "..."
    }
  ]
}
```

---

# 21. Course Content Schema

Full course representation:

```json id="91e8fw"
{
  "course": {
    "title": "Basis Data",
    "code": "IF123"
  },
  "weeks": [
    {
      "week_number": 1,
      "title": "Introduction",
      "items": []
    },
    {
      "week_number": 2,
      "title": "Relational Model",
      "items": []
    }
  ]
}
```

Jumlah week mengikuti RPS.

---

# 22. Content Item Identity

Setiap content item memiliki internal identity.

```json id="m6dvvy"
{
  "id": "content-uuid",
  "type": "learning_material",
  "version": 1
}
```

Regeneration:

```text id="j5yyif"
content-uuid
 ├── v1
 ├── v2
 └── v3
```

Moodle object ID disimpan separately pada Moodle execution/mapping layer.

---

# 23. Traceability Schema

Generated object sebaiknya menyimpan source reference.

```json id="7h9yhf"
{
  "source": {
    "rps_id": "...",
    "rps_analysis_id": "...",
    "course_plan_id": "...",
    "course_plan_week_id": "...",
    "learning_outcomes": [
      "LO-1"
    ],
    "objectives": [
      "OBJ-1"
    ]
  }
}
```

Tujuannya agar validator dapat melakukan traceability.

---

# 24. Generation Metadata

Generated content dapat memiliki:

```json id="3gvqj9"
{
  "generation": {
    "agent_run_id": "...",
    "model": "model-name",
    "runtime": "ollama",
    "generated_at": "timestamp"
  }
}
```

Model name harus mencerminkan model aktual yang digunakan.

---

# 25. Validation Schema

Validation result:

```json id="v4ip2d"
{
  "status": "PASS",
  "checks": [
    {
      "type": "schema",
      "status": "PASS",
      "message": null
    },
    {
      "type": "rps_adherence",
      "status": "PASS",
      "message": null
    },
    {
      "type": "consistency",
      "status": "PASS",
      "message": null
    }
  ],
  "errors": [],
  "warnings": []
}
```

---

# 26. Validation Check Types

Recommended:

```text
schema
rps_adherence
course_plan_alignment
content_consistency
activity_configuration
completeness
moodle_readiness
```

Exact validation implementation remains defined in Testing & Quality documentation.

---

# 27. Validation Error

```json id="5zv6br"
{
  "type": "rps_adherence",
  "severity": "ERROR",
  "field": "topic",
  "message": "Generated topic does not match approved course plan."
}
```

Severity:

```text
ERROR
WARNING
INFO
```

---

# 28. Generation Request Schema

Backend dapat mengirim request ke Agent menggunakan structured input.

```json id="ex3fob"
{
  "task": "generate_week_content",
  "course_id": "...",
  "course_plan_id": "...",
  "week_number": 5,
  "context": {
    "rps_analysis": {},
    "instructor_profile": {},
    "additional_prompt": "..."
  },
  "activity_config": {
    "learning_material": true,
    "assignment": true,
    "quiz": false
  }
}
```

LLM tidak perlu menerima seluruh database object.

Backend melakukan context preparation.

---

# 29. Generation Response Schema

```json id="nq5x2y"
{
  "status": "SUCCESS",
  "content": {
    "week_number": 5,
    "items": []
  },
  "warnings": []
}
```

Jika gagal:

```json id="f3a6z9"
{
  "status": "FAILED",
  "content": null,
  "errors": [
    {
      "type": "INVALID_OUTPUT",
      "message": "Output does not conform to required schema."
    }
  ]
}
```

---

# 30. Tool Request Schema

Agent tool request:

```json id="q6u0sn"
{
  "tool": "moodle.create_learning_material",
  "arguments": {
    "course_id": "...",
    "section_id": "...",
    "title": "...",
    "content": "..."
  }
}
```

Tool request harus melewati backend validation.

---

# 31. Tool Response Schema

Success:

```json id="l7y9lq"
{
  "success": true,
  "operation": "create_learning_material",
  "object_id": "123"
}
```

Failure:

```json id="3w7c48"
{
  "success": false,
  "operation": "create_learning_material",
  "error": {
    "code": "MOODLE_PERMISSION_DENIED",
    "retryable": false
  }
}
```

---

# 32. Moodle Mapping Schema

Internal content tidak boleh langsung memiliki Moodle-specific implementation fields secara berlebihan.

Gunakan mapping:

```json id="r3fl3m"
{
  "internal_content_id": "...",
  "moodle": {
    "course_id": "123",
    "section_id": "456",
    "module_id": "789",
    "instance_id": "..."
  }
}
```

Exact fields bergantung pada Moodle object type.

---

# 33. Execution Request

Moodle execution dapat menggunakan:

```json id="j0z7wo"
{
  "course_id": "...",
  "items": [
    {
      "content_id": "...",
      "action": "create"
    }
  ]
}
```

Backend menerjemahkan request menjadi Moodle operations.

Agent tidak membuat raw Moodle payload.

---

# 34. Verification Schema

```json id="h5j4n0"
{
  "status": "PASS",
  "target": {
    "type": "learning_material",
    "internal_id": "..."
  },
  "expected": {
    "title": "Introduction to Database"
  },
  "actual": {
    "title": "Introduction to Database"
  },
  "discrepancies": []
}
```

---

# 35. Verification Status

```text
PASS
PARTIAL
FAIL
UNKNOWN
```

`UNKNOWN` digunakan ketika property tidak dapat diverifikasi.

---

# 36. Schema Validation Rules

Minimum validation:

### Required

* object type;
* required identifiers;
* title;
* week number where applicable;
* content structure.

### Type

* string;
* integer;
* boolean;
* array;
* object.

### Enum

Activity types harus berasal dari allowed values.

```text
learning_material
resource
assignment
quiz
```

---

# 37. Academic Validation Rules

Content tidak cukup hanya valid secara JSON.

Contoh:

```text id="q3k2xj"
RPS:
Week 4 → Normalization

Generated:
Week 4 → Web Programming
```

Schema:

```text
VALID
```

Academic validation:

```text
FAIL
```

Karena itu schema validation dan semantic/RPS validation merupakan dua tahap berbeda.

---

# 38. Content Consistency Rules

Validator harus memeriksa:

```text
Course title consistency
Week numbering
Topic consistency
Learning outcome references
Objective references
Activity configuration
Content relationship
```

Contoh:

Jika:

```text
assignment.enabled = false
```

tetapi generated output memiliki assignment:

```text
FAIL
```

---

# 39. Instructor Profile Rules

Instructor Profile dapat memengaruhi:

```text
presentation style
language
depth
examples
formatting
```

Tidak boleh mengubah:

```text
course identity
RPS learning outcomes
RPS weekly distribution
academic facts
```

---

# 40. Additional Prompt Rules

Additional Prompt diperlakukan sebagai instruction dengan batasan.

```text
System Constraints
        >
RPS
        >
Instructor Profile
        >
Additional Prompt
```

Jika Additional Prompt bertentangan dengan RPS:

```text
RPS constraint wins
```

dan conflict harus dapat dijelaskan kepada instructor.

---

# 41. Content Status

Recommended content status:

```text
DRAFT
GENERATED
VALIDATED
PENDING_REVIEW
APPROVED
REJECTED
EXECUTED
VERIFIED
FAILED
```

State transition dikontrol Backend.

---

# 42. Content Generation Granularity

Supported:

```text
Course
Week
Content Item
Activity
```

MVP priority:

```text
Course Plan
Week
Content Item
```

Regenerating one item tidak boleh menghapus item lain yang telah approved.

---

# 43. Versioning

Generated content menggunakan version number.

```text
{
  "id": "...",
  "version": 2
}
```

Rules:

1. Version immutable.
2. Regeneration creates new version.
3. Previous version retained.
4. Approved version identified explicitly.
5. Moodle execution references approved version.

---

# 44. Schema Evolution

Schema dapat berubah selama development.

Versioning dapat diperkenalkan:

```json id="y7v5e1"
{
  "schema_version": "1.0"
}
```

Jika perubahan bersifat breaking:

```text
1.0 → 2.0
```

Jika backward-compatible:

```text
1.0 → 1.1
```

Schema version tidak sama dengan content version.

---

# 45. JSON Schema Implementation

Production implementation sebaiknya menggunakan JSON Schema atau Pydantic models.

Recommended backend direction:

```text
JSON Schema / Pydantic
        ↓
Validation
        ↓
Persistence
```

FastAPI/Python dapat menggunakan Pydantic sebagai application-level schema definition.

Exact implementation remains an engineering decision.

---

# 46. Database Mapping

| Schema Object     | Database Entity      |
| ----------------- | -------------------- |
| RPS Analysis      | `rps_analyses`       |
| Course Plan       | `course_plans`       |
| Course Plan Week  | `course_plan_weeks`  |
| Learning Material | `contents`           |
| Resource          | `contents`           |
| Assignment        | `activities`         |
| Quiz              | `activities`         |
| Validation        | `validation_results` |
| Agent Run         | `agent_runs`         |
| Verification      | `verifications`      |

Structured content dapat disimpan pada JSONB.

---

# 47. Moodle Mapping Boundary

Schema internal harus tetap Moodle-independent.

```text
Internal Content Schema
        ↓
Moodle Adapter
        ↓
Moodle-specific representation
```

Jangan membuat content schema:

```text
{
  "moodle_modname": "...",
  "moodle_cm_id": "...",
  "moodle_instance": "..."
}
```

sebagai bagian inti generated content.

Moodle-specific fields berada pada integration layer.

---

# 48. Example Full Week

```json id="ngm6j3"
{
  "week_number": 5,
  "title": "Database Normalization",
  "learning_outcomes": [
    "LO-3"
  ],
  "objectives": [
    "OBJ-5"
  ],
  "items": [
    {
      "type": "learning_material",
      "title": "Introduction to Normalization",
      "content": {
        "summary": "...",
        "sections": [
          {
            "title": "First Normal Form",
            "content": "..."
          },
          {
            "title": "Second Normal Form",
            "content": "..."
          }
        ]
      }
    },
    {
      "type": "assignment",
      "title": "Normalization Exercise",
      "description": "...",
      "instructions": []
    }
  ]
}
```

---

# 49. Example Course

```json id="o1qg6x"
{
  "schema_version": "1.0",
  "course": {
    "title": "Basis Data",
    "code": "IF123"
  },
  "weeks": [
    {
      "week_number": 1,
      "title": "Introduction",
      "items": []
    },
    {
      "week_number": 2,
      "title": "Relational Model",
      "items": []
    },
    {
      "week_number": 3,
      "title": "SQL",
      "items": []
    }
  ]
}
```

---

# 50. Example Generation → Validation

```text id="u5uv0s"
Agent
 ↓
Generate JSON
 ↓
Schema Validation
 ├── FAIL → Regenerate
 └── PASS
       ↓
RPS Validation
 ├── FAIL → Fix/Regenerate
 └── PASS
       ↓
Instructor Review
 ├── Reject → Regenerate
 └── Approve
       ↓
Moodle Execution
```

---

# 51. MVP Schema Boundary

MVP wajib memiliki schema untuk:

1. RPS Analysis.
2. Course Plan.
3. Weekly Plan.
4. Learning Material.
5. Activity Configuration.
6. Assignment.
7. Quiz — jika capability Moodle tersedia.
8. Validation Result.
9. Tool Request/Response.
10. Verification Result.

MVP tidak perlu langsung mendukung schema untuk:

* attendance;
* forum;
* workshop;
* lesson;
* advanced grading;
* complex question bank;
* SCORM;
* H5P;
* seluruh Moodle activity types.

---

# 52. Open Decisions

| Decision                          | Status   |
| --------------------------------- | -------- |
| Final JSON Schema                 | TBD      |
| Pydantic model structure          | TBD      |
| Schema versioning implementation  | TBD      |
| Exact RPS analysis fields         | TBD      |
| Exact learning material structure | Proposed |
| Assignment schema                 | Proposed |
| Quiz schema                       | Proposed |
| Rubric schema                     | TBD      |
| Resource handling                 | Proposed |
| External reference verification   | TBD      |
| Moodle-specific mapping           | TBD      |

---

# 53. Definition of Done

Content Schema dianggap siap untuk implementation apabila:

1. RPS Analysis schema dapat diparse.
2. Course Plan schema dapat diparse.
3. Weekly content dapat diparse.
4. Learning material memiliki struktur konsisten.
5. Assignment dan Quiz memiliki schema terpisah.
6. Activity configuration dapat mengontrol generation.
7. Validation result memiliki struktur standar.
8. Tool request/response memiliki contract.
9. Verification result memiliki contract.
10. Versioning strategy jelas.
11. Traceability ke RPS dapat dilakukan.
12. Schema tidak bergantung langsung pada Moodle-specific implementation.

---

# 54. Final Data Flow

```text
┌───────────────┐
│   RPS File    │
└───────┬───────┘
        ↓
┌───────────────┐
│ RPS Analysis  │
└───────┬───────┘
        ↓
┌───────────────┐
│  Course Plan  │
└───────┬───────┘
        ↓
┌───────────────┐
│  Weekly Plan  │
└───────┬───────┘
        ↓
┌────────────────────────┐
│ Generated Content      │
│                        │
│ Material               │
│ Resource               │
│ Assignment (optional)  │
│ Quiz (optional)        │
└───────────┬────────────┘
            ↓
┌────────────────────────┐
│       Validation       │
└───────────┬────────────┘
            ↓
┌────────────────────────┐
│   Instructor Review    │
└───────────┬────────────┘
            ↓
┌────────────────────────┐
│    Moodle Mapping      │
└───────────┬────────────┘
            ↓
┌────────────────────────┐
│    Moodle Execution    │
└───────────┬────────────┘
            ↓
┌────────────────────────┐
│      Verification      │
└────────────────────────┘
```

---

# 55. Document Status

**Status: Proposed**

Schema utama telah ditentukan secara konseptual dan dapat digunakan sebagai dasar implementasi.

Detail yang masih dapat berubah:

* final JSON Schema;
* exact Pydantic models;
* final RPS analysis fields;
* quiz/assignment fields;
* Moodle-specific mappings;
* validation scoring;
* schema versioning implementation.

Perubahan schema yang memengaruhi API, database, agent prompt, atau Moodle integration harus dievaluasi terhadap dokumen terkait.
