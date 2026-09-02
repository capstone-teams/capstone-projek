# Data Model

## 1. Document Information

| Item              | Value                                                          |
| ----------------- | -------------------------------------------------------------- |
| Document          | Data Model                                                     |
| Project           | Agentic AI untuk Mengisi Konten Moodle                         |
| Status            | Proposed                                                       |
| Database          | PostgreSQL — Proposed                                          |
| Owner             | Capstone Team                                                  |
| Related Documents | Project Charter, PRD, System Design, Moodle Integration Design |

---

## 2. Purpose

Dokumen ini mendefinisikan model data utama yang digunakan sistem untuk menyimpan:

* user dan role;
* instructor profile;
* RPS;
* hasil processing dan analysis RPS;
* course;
* course plan;
* weekly content;
* activity configuration;
* generated content;
* validation;
* instructor review;
* agent execution;
* Moodle execution;
* verification;
* monitoring events.

Model dibuat untuk mendukung workflow:

```text
RPS
 ↓
Processing
 ↓
Analysis
 ↓
Course Planning
 ↓
Content Generation
 ↓
Validation
 ↓
Review
 ↓
Moodle Execution
 ↓
Verification
```

---

# 3. Data Modeling Principles

## 3.1 RPS sebagai Academic Source of Truth

Data akademik yang berasal dari RPS harus dapat ditelusuri kembali ke sumbernya.

Sistem tidak boleh hanya menyimpan hasil akhir LLM tanpa menyimpan hubungan dengan RPS.

```text
RPS
 ↓
RPS Analysis
 ↓
Course Plan
 ↓
Generated Content
```

Setiap generated content harus dapat ditelusuri secara konseptual ke bagian course plan/RPS yang menjadi basisnya.

---

## 3.2 Generated Data dan Source Data Dipisahkan

Data input dan output AI tidak boleh dicampur.

Contoh:

```text
RPS
 └── source data

Generated Content
 └── AI output
```

Hal ini memungkinkan:

* regeneration;
* comparison;
* validation;
* audit;
* rollback;
* traceability.

---

## 3.3 Database sebagai State Authority

Database menjadi source of truth untuk state aplikasi.

LLM tidak menjadi source of truth.

Moodle juga tidak menjadi source of truth untuk workflow aplikasi.

```text
Frontend
   ↓
Backend
   ↓
Database ← Application State
   ↓
Moodle
```

Moodle merupakan external execution system.

---

# 4. High-Level Entity Model

Entity utama:

```text
User
 │
 ├── InstructorProfile
 │
 └── Role

User
 │
 └── RPS
       │
       └── RPSAnalysis
              │
              ▼
          CoursePlan
              │
              └── CoursePlanWeek
                     │
                     └── Content
                            │
                            └── Activity

Course
 │
 ├── CoursePlan
 │
 └── MoodleExecution

AgentRun
 │
 ├── AgentEvent
 ├── ValidationResult
 └── Review

MoodleExecution
 │
 └── Verification
```

---

# 5. Entity List

| Entity            | Purpose                              |
| ----------------- | ------------------------------------ |
| User              | Application user                     |
| InstructorProfile | Instructor personalization           |
| RPS               | Uploaded RPS document                |
| RPSAnalysis       | Structured interpretation of RPS     |
| Course            | Application representation of course |
| CoursePlan        | Generated course structure           |
| CoursePlanWeek    | Weekly plan                          |
| Content           | Generated learning content           |
| Activity          | Optional learning activity           |
| AgentRun          | One execution of agent workflow      |
| AgentEvent        | Operational workflow event           |
| ValidationResult  | Validation output                    |
| Review            | Instructor review decision           |
| MoodleExecution   | Moodle operation/execution record    |
| Verification      | Post-execution verification          |

---

# 6. User

Represents an application user.

Conceptual fields:

| Field         | Type      | Description                                   |
| ------------- | --------- | --------------------------------------------- |
| id            | UUID      | Primary key                                   |
| name          | String    | Display name                                  |
| email         | String    | User email                                    |
| password_hash | String    | Password hash if local authentication is used |
| role          | Enum      | Instructor / Student / Admin                  |
| status        | Enum      | Active / Inactive                             |
| created_at    | Timestamp | Creation time                                 |
| updated_at    | Timestamp | Last update                                   |

### Role

Minimum roles:

```text
INSTRUCTOR
STUDENT
ADMIN
```

The Student role exists primarily to support course access and verification.

Full student management is outside project scope.

---

# 7. Instructor Profile

Stores instructor-specific preferences.

Conceptual fields:

| Field                  | Type      | Description                 |
| ---------------------- | --------- | --------------------------- |
| id                     | UUID      | Primary key                 |
| user_id                | UUID      | FK → User                   |
| teaching_style         | JSONB     | Teaching style/preferences  |
| language               | String    | Preferred language          |
| content_preferences    | JSONB     | Content preferences         |
| activity_preferences   | JSONB     | Assignment/quiz preferences |
| additional_preferences | JSONB     | Other supported preferences |
| created_at             | Timestamp | Creation time               |
| updated_at             | Timestamp | Last update                 |

Instructor Profile is optional.

It modifies how content is presented but must not override academic constraints from the RPS.

---

# 8. RPS

Represents an uploaded RPS document.

Conceptual fields:

| Field           | Type      | Description                                |
| --------------- | --------- | ------------------------------------------ |
| id              | UUID      | Primary key                                |
| owner_id        | UUID      | FK → User                                  |
| file_name       | String    | Original filename                          |
| file_type       | String    | PDF / DOCX                                 |
| file_path       | String    | Stored document location                   |
| file_hash       | String    | Integrity/deduplication hash               |
| status          | Enum      | Uploaded / Processing / Processed / Failed |
| source_markdown | Text      | Normalized Markdown representation         |
| structured_data | JSONB     | Extracted structured data                  |
| created_at      | Timestamp | Upload time                                |
| updated_at      | Timestamp | Last update                                |

The original file should be retained when practical so the generated result remains traceable to its source.

---

# 9. RPS Analysis

Represents structured interpretation of an RPS.

Conceptual fields:

| Field               | Type      | Description                  |
| ------------------- | --------- | ---------------------------- |
| id                  | UUID      | Primary key                  |
| rps_id              | UUID      | FK → RPS                     |
| version             | Integer   | Analysis version             |
| course_identity     | JSONB     | Course information           |
| learning_outcomes   | JSONB     | Learning outcomes            |
| objectives          | JSONB     | Learning objectives          |
| topics              | JSONB     | Topics                       |
| weekly_distribution | JSONB     | Weekly distribution          |
| teaching_methods    | JSONB     | Methods                      |
| assessments         | JSONB     | Assessment information       |
| references          | JSONB     | References                   |
| raw_analysis        | JSONB     | Complete structured analysis |
| created_at          | Timestamp | Creation time                |

The schema remains flexible because RPS formats can differ.

---

# 10. Course

Represents a course in the application.

Conceptual fields:

| Field            | Type      | Description               |
| ---------------- | --------- | ------------------------- |
| id               | UUID      | Primary key               |
| instructor_id    | UUID      | FK → User                 |
| rps_id           | UUID      | FK → RPS                  |
| name             | String    | Course name               |
| code             | String    | Course code               |
| description      | Text      | Course description        |
| semester         | String    | Semester identifier       |
| status           | Enum      | Draft / Active / Archived |
| moodle_course_id | String    | External Moodle course ID |
| created_at       | Timestamp | Creation time             |
| updated_at       | Timestamp | Last update               |

`moodle_course_id` may be null until Moodle execution occurs.

---

# 11. Course Plan

Represents the AI-generated high-level course structure.

Conceptual fields:

| Field                     | Type      | Description                                              |
| ------------------------- | --------- | -------------------------------------------------------- |
| id                        | UUID      | Primary key                                              |
| course_id                 | UUID      | FK → Course                                              |
| rps_analysis_id           | UUID      | FK → RPSAnalysis                                         |
| version                   | Integer   | Plan version                                             |
| status                    | Enum      | Draft / Validated / Pending Review / Approved / Rejected |
| plan_data                 | JSONB     | Structured course plan                                   |
| generated_by_agent_run_id | UUID      | FK → AgentRun                                            |
| created_at                | Timestamp | Creation time                                            |
| updated_at                | Timestamp | Last update                                              |

Versioning is important because instructor may regenerate the course plan.

Example:

```text
Course Plan v1
Course Plan v2
Course Plan v3
```

Only an approved version should become the basis for Moodle execution.

---

# 12. Course Plan Week

Represents one weekly unit in a course plan.

Conceptual fields:

| Field             | Type      | Description                |
| ----------------- | --------- | -------------------------- |
| id                | UUID      | Primary key                |
| course_plan_id    | UUID      | FK → CoursePlan            |
| week_number       | Integer   | Week number                |
| title             | String    | Weekly topic/title         |
| learning_outcomes | JSONB     | Weekly outcomes            |
| topics            | JSONB     | Weekly topics              |
| methods           | JSONB     | Teaching methods           |
| assessment        | JSONB     | Planned assessment         |
| metadata          | JSONB     | Additional structured data |
| created_at        | Timestamp | Creation time              |
| updated_at        | Timestamp | Last update                |

The number of weeks should follow the RPS.

The system may support up to 16 weeks as a common semester structure, but 16 is not a hard requirement unless the RPS specifies it.

---

# 13. Content

Represents generated learning material.

Conceptual fields:

| Field                     | Type      | Description                                              |
| ------------------------- | --------- | -------------------------------------------------------- |
| id                        | UUID      | Primary key                                              |
| course_plan_week_id       | UUID      | FK → CoursePlanWeek                                      |
| title                     | String    | Content title                                            |
| content_type              | Enum      | Learning Material / Resource                             |
| content_data              | JSONB     | Structured content                                       |
| content_markdown          | Text      | Markdown representation                                  |
| version                   | Integer   | Content version                                          |
| status                    | Enum      | Draft / Validated / Pending Review / Approved / Rejected |
| generated_by_agent_run_id | UUID      | FK → AgentRun                                            |
| created_at                | Timestamp | Creation time                                            |
| updated_at                | Timestamp | Last update                                              |

Content must support versioning.

Example:

```text
Material Week 3
 ├── v1
 ├── v2
 └── v3
```

Regeneration should create a new version rather than silently destroying the previous result.

---

# 14. Activity

Represents an optional Moodle learning activity.

Conceptual fields:

| Field               | Type      | Description                             |
| ------------------- | --------- | --------------------------------------- |
| id                  | UUID      | Primary key                             |
| course_plan_week_id | UUID      | FK → CoursePlanWeek                     |
| type                | Enum      | Assignment / Quiz                       |
| title               | String    | Activity title                          |
| activity_data       | JSONB     | Activity configuration/content          |
| enabled             | Boolean   | Whether instructor requested it         |
| version             | Integer   | Activity version                        |
| status              | Enum      | Draft / Validated / Approved / Executed |
| created_at          | Timestamp | Creation time                           |
| updated_at          | Timestamp | Last update                             |

Activity generation is controlled by instructor configuration.

Example:

```json
{
  "learning_material": true,
  "assignment": true,
  "quiz": false
}
```

The system must not generate Assignment or Quiz merely because those activity types are technically supported.

---

# 15. Agent Run

Represents one execution of the agent workflow.

Example:

```text
Generate Course Plan
Generate Week 1 Content
Generate Entire Course
Regenerate Week 4
Execute Moodle Course
```

Conceptual fields:

| Field            | Type      | Description                                                              |
| ---------------- | --------- | ------------------------------------------------------------------------ |
| id               | UUID      | Primary key                                                              |
| course_id        | UUID      | FK → Course                                                              |
| run_type         | Enum      | Analysis / Planning / Generation / Validation / Execution / Verification |
| status           | Enum      | Created / Running / Waiting / Retrying / Failed / Completed              |
| current_stage    | String    | Current workflow stage                                                   |
| model_name       | String    | LLM model used                                                           |
| model_runtime    | String    | Runtime, e.g. Ollama                                                     |
| input_context    | JSONB     | Structured input metadata                                                |
| output_reference | JSONB     | Output reference                                                         |
| retry_count      | Integer   | Retry count                                                              |
| started_at       | Timestamp | Start time                                                               |
| completed_at     | Timestamp | Completion time                                                          |
| created_at       | Timestamp | Creation time                                                            |

Sensitive data must not be stored in `input_context`.

---

# 16. Agent Event

Represents an operational event during an agent run.

Example events:

```text
RPS_PROCESSING_STARTED
RPS_PROCESSING_COMPLETED
RPS_ANALYSIS_STARTED
COURSE_PLAN_GENERATED
VALIDATION_STARTED
VALIDATION_FAILED
WAITING_INSTRUCTOR_REVIEW
MOODLE_EXECUTION_STARTED
MOODLE_EXECUTION_COMPLETED
VERIFICATION_FAILED
RETRY_STARTED
```

Conceptual fields:

| Field        | Type      | Description            |
| ------------ | --------- | ---------------------- |
| id           | UUID      | Primary key            |
| agent_run_id | UUID      | FK → AgentRun          |
| event_type   | String    | Event identifier       |
| stage        | String    | Workflow stage         |
| status       | String    | Event status           |
| message      | Text      | Human-readable message |
| metadata     | JSONB     | Non-sensitive metadata |
| created_at   | Timestamp | Event time             |

Agent Event is intended for monitoring and audit.

It must not store hidden chain-of-thought.

---

# 17. Validation Result

Represents validation performed on generated output.

Conceptual fields:

| Field        | Type      | Description                                         |
| ------------ | --------- | --------------------------------------------------- |
| id           | UUID      | Primary key                                         |
| agent_run_id | UUID      | FK → AgentRun                                       |
| target_type  | Enum      | Course Plan / Content / Activity / Moodle Execution |
| target_id    | UUID      | Target entity                                       |
| status       | Enum      | Passed / Failed / Partial                           |
| checks       | JSONB     | Individual validation checks                        |
| score        | Numeric   | Optional score                                      |
| errors       | JSONB     | Validation errors                                   |
| warnings     | JSONB     | Validation warnings                                 |
| created_at   | Timestamp | Validation time                                     |

Validation categories may include:

```text
RPS adherence
Structural completeness
Content consistency
Configuration compliance
Moodle readiness
```

Exact scoring methodology remains TBD.

---

# 18. Review

Represents instructor review.

Conceptual fields:

| Field       | Type      | Description                          |
| ----------- | --------- | ------------------------------------ |
| id          | UUID      | Primary key                          |
| reviewer_id | UUID      | FK → User                            |
| target_type | Enum      | Course Plan / Content / Activity     |
| target_id   | UUID      | Target entity                        |
| decision    | Enum      | Approved / Rejected / Edit Requested |
| comment     | Text      | Review comment                       |
| created_at  | Timestamp | Review time                          |

Possible flow:

```text
Generated
   ↓
Validated
   ↓
Instructor Review
   ├── Approve
   ├── Reject
   └── Request Edit/Regenerate
```

---

# 19. Moodle Execution

Represents an operation performed against Moodle.

Conceptual fields:

| Field             | Type      | Description                                               |
| ----------------- | --------- | --------------------------------------------------------- |
| id                | UUID      | Primary key                                               |
| course_id         | UUID      | FK → Course                                               |
| agent_run_id      | UUID      | FK → AgentRun                                             |
| operation         | String    | Moodle operation                                          |
| target_type       | String    | Course / Section / Content / Activity                     |
| target_id         | UUID      | Internal target                                           |
| moodle_object_id  | String    | External Moodle ID                                        |
| status            | Enum      | Pending / Running / Success / Failed / Blocked / Retrying |
| request_reference | String    | Internal operation reference                              |
| error_code        | String    | Normalized error                                          |
| error_message     | Text      | Safe error message                                        |
| retry_count       | Integer   | Retry count                                               |
| started_at        | Timestamp | Execution start                                           |
| completed_at      | Timestamp | Execution end                                             |

Raw authentication information must never be stored.

---

# 20. Verification

Represents verification after Moodle execution.

Conceptual fields:

| Field         | Type      | Description                           |
| ------------- | --------- | ------------------------------------- |
| id            | UUID      | Primary key                           |
| course_id     | UUID      | FK → Course                           |
| execution_id  | UUID      | FK → MoodleExecution                  |
| target_type   | String    | Course / Section / Content / Activity |
| target_id     | UUID      | Internal target                       |
| status        | Enum      | Pass / Partial / Fail / Unknown       |
| expected_data | JSONB     | Expected state                        |
| actual_data   | JSONB     | Retrieved Moodle state                |
| discrepancies | JSONB     | Differences                           |
| verified_at   | Timestamp | Verification time                     |

Verification should compare expected and actual state rather than merely checking whether an API call returned successfully.

---

# 21. Entity Relationships

Conceptual relationship:

```text
User
 │
 ├───────────────┐
 │               │
 ▼               ▼
Instructor     RPS
Profile          │
                 ▼
             RPSAnalysis
                 │
                 ▼
               Course
                 │
                 ▼
             CoursePlan
                 │
                 ▼
          CoursePlanWeek
             │       │
             │       └──────────────┐
             ▼                      ▼
          Content                Activity
             │                      │
             └──────────┬───────────┘
                        │
                        ▼
                    AgentRun
                        │
             ┌──────────┼──────────┐
             ▼          ▼          ▼
       AgentEvent   Validation   Review
                                   │
                                   ▼
                           MoodleExecution
                                   │
                                   ▼
                              Verification
```

---

# 22. Cardinality

Recommended relationships:

| Relationship                   | Cardinality |
| ------------------------------ | ----------- |
| User → InstructorProfile       | 1 : 0..1    |
| User → RPS                     | 1 : N       |
| RPS → RPSAnalysis              | 1 : N       |
| Instructor → Course            | 1 : N       |
| RPS → Course                   | 1 : N       |
| Course → CoursePlan            | 1 : N       |
| CoursePlan → CoursePlanWeek    | 1 : N       |
| CoursePlanWeek → Content       | 1 : N       |
| CoursePlanWeek → Activity      | 1 : N       |
| Course → AgentRun              | 1 : N       |
| AgentRun → AgentEvent          | 1 : N       |
| AgentRun → ValidationResult    | 1 : N       |
| User → Review                  | 1 : N       |
| Course → MoodleExecution       | 1 : N       |
| MoodleExecution → Verification | 1 : N       |

---

# 23. Versioning Strategy

Versioning diperlukan untuk AI-generated content.

Contoh:

```text
Course Plan
 ├── Version 1
 └── Version 2

Week 5 Material
 ├── Version 1
 ├── Version 2
 └── Version 3
```

Recommended rule:

* old versions remain immutable;
* new generation creates a new version;
* only one version can be active/approved at a time;
* Moodle execution references the approved version.

---

# 24. Traceability

Traceability merupakan requirement penting.

Ideal relationship:

```text
RPS
 ↓
RPS Analysis
 ↓
Course Plan
 ↓
Week
 ↓
Content
 ↓
Validation
 ↓
Review
 ↓
Moodle Execution
 ↓
Verification
```

Contoh:

```text
RPS section:
Learning Outcome 3

        ↓

Course Plan:
Week 8

        ↓

Content:
Database Normalization

        ↓

Validation:
RPS adherence PASS

        ↓

Review:
APPROVED

        ↓

Moodle:
Week 8 / Material ID 123

        ↓

Verification:
PASS
```

---

# 25. Activity Configuration

Activity configuration dapat disimpan pada level course atau generation run.

Contoh:

```json
{
  "learning_material": true,
  "assignment": true,
  "quiz": false
}
```

Future configuration:

```json
{
  "assignment": {
    "enabled": true,
    "count": 1
  },
  "quiz": {
    "enabled": true,
    "count": 5
  }
}
```

Schema final masih dapat berubah setelah `content-schema.md` ditentukan.

---

# 26. JSONB Usage

PostgreSQL JSONB digunakan untuk data yang:

* memiliki struktur variatif;
* berasal dari RPS;
* merupakan output AI;
* memiliki schema yang masih berkembang;
* membutuhkan extensibility.

Contoh kandidat JSONB:

```text
RPS.structured_data
RPSAnalysis.raw_analysis
CoursePlan.plan_data
CoursePlanWeek.learning_outcomes
Content.content_data
Activity.activity_data
AgentRun.input_context
AgentEvent.metadata
ValidationResult.checks
MoodleExecution metadata
Verification.expected_data
Verification.actual_data
```

Namun JSONB tidak boleh digunakan untuk semua field.

Data yang:

* sering dicari;
* memiliki relationship;
* membutuhkan foreign key;
* merupakan identifier;
* merupakan status;

sebaiknya tetap menjadi relational column.

---

# 27. Database Constraints

Minimum constraints:

### User

```text
email UNIQUE
```

### RPS

```text
file_hash INDEX
owner_id FOREIGN KEY
```

### Course

```text
instructor_id FOREIGN KEY
rps_id FOREIGN KEY
```

### CoursePlan

```text
(course_id, version) UNIQUE
```

### CoursePlanWeek

```text
(course_plan_id, week_number) UNIQUE
```

### Content

Version uniqueness dapat menggunakan:

```text
(parent_content_identity, version) UNIQUE
```

Implementasi exact identity masih perlu ditentukan.

### Activity

Activity harus memiliki valid course/week relationship.

### Moodle Mapping

External Moodle IDs sebaiknya di-index untuk lookup cepat.

---

# 28. Indexing

Minimum indexes:

```text
users.email
rps.owner_id
rps.status
courses.instructor_id
courses.moodle_course_id
course_plans.course_id
course_plan_weeks.course_plan_id
contents.course_plan_week_id
activities.course_plan_week_id
agent_runs.course_id
agent_runs.status
agent_events.agent_run_id
agent_events.created_at
moodle_executions.course_id
moodle_executions.status
verification.course_id
```

Index tambahan ditentukan setelah query pattern backend diketahui.

Jangan melakukan premature indexing pada semua JSONB fields.

---

# 29. Deletion Strategy

Data akademik dan AI-generated content memiliki nilai audit.

Karena itu, hard delete tidak boleh menjadi default untuk semua entity.

Recommended:

```text
User → deactivate
Course → archive
RPS → retain/archive
CoursePlan → retain versions
Content → retain versions
AgentRun → retain
MoodleExecution → retain
Verification → retain
```

Penghapusan permanen harus mengikuti kebijakan data proyek yang ditentukan kemudian.

---

# 30. Sensitive Data

Database tidak boleh menyimpan:

```text
Moodle password
Moodle token in plain text
LLM secret/API key
Authentication header
```

Jika credential Moodle perlu disimpan oleh sistem, mekanisme secure secret storage/encryption masih `TBD`.

---

# 31. Agent State vs Database State

Agent internal state tidak boleh menjadi satu-satunya sumber workflow.

Contoh:

```text
Agent memory/state
        ↓
Persisted AgentRun
        ↓
AgentEvent
        ↓
Database
```

Jika agent process berhenti:

```text
Process crash
    ↓
Backend reads AgentRun
    ↓
Determine last persisted state
    ↓
Resume / Retry / Fail
```

Dengan demikian workflow tidak bergantung pada memory process.

---

# 32. Monitoring Data

Monitoring UI membutuhkan data dari:

```text
AgentRun
AgentEvent
ValidationResult
MoodleExecution
Verification
```

Contoh tampilan:

```text
Course Generation

RPS Processing       ✓
RPS Analysis         ✓
Course Planning      ✓
Plan Review          ✓
Content Generation   ███████░░
Validation           Pending
Moodle Execution     Pending
Verification         Pending
```

Monitoring menampilkan operational state.

Monitoring tidak menampilkan hidden chain-of-thought atau internal reasoning lengkap LLM.

---

# 33. Transaction Boundary

Database transaction digunakan pada perubahan state yang harus konsisten.

Contoh:

```text
Create Moodle Execution
+
Update Agent Run
+
Create Event
```

Ketiganya perlu dipertimbangkan sebagai satu logical state transition.

Sebaliknya, external Moodle API call tidak boleh diasumsikan atomic dengan database transaction.

Pattern:

```text
DB → mark operation RUNNING
 ↓
Moodle API call
 ↓
DB → SUCCESS / FAILED
```

---

# 34. External ID Mapping

Moodle IDs merupakan external identifiers.

Contoh:

```text
Internal:
course.id = UUID

External:
moodle_course_id = "123"
```

Untuk activity:

```text
internal activity.id
        ↕
moodle module/corresponding instance ID
```

Exact Moodle object mapping remains dependent on selected activity/resource type.

---

# 35. Data Lifecycle

```text
RPS Uploaded
     ↓
Processed
     ↓
Analyzed
     ↓
Course Created
     ↓
Plan Generated
     ↓
Plan Approved
     ↓
Content Generated
     ↓
Content Approved
     ↓
Moodle Executed
     ↓
Verified
```

Setiap tahap harus memiliki persisted state.

---

# 36. Minimal MVP Tables

Untuk menghindari overengineering, MVP minimum dapat dimulai dari:

```text
users
instructor_profiles
rps
rps_analyses
courses
course_plans
course_plan_weeks
contents
activities
agent_runs
agent_events
validation_results
reviews
moodle_executions
verifications
```

Tidak perlu langsung membuat tabel tambahan untuk setiap konsep kecil.

Jika sebuah data belum membutuhkan relationship atau query independen, JSONB dapat digunakan terlebih dahulu.

---

# 37. Initial PostgreSQL Schema Direction

Secara konseptual:

```text
users
  │
  ├── instructor_profiles
  │
  ├── rps
  │      └── rps_analyses
  │
  └── courses
          │
          ├── course_plans
          │       └── course_plan_weeks
          │               ├── contents
          │               └── activities
          │
          ├── agent_runs
          │       ├── agent_events
          │       └── validation_results
          │
          ├── reviews
          │
          ├── moodle_executions
          │
          └── verifications
```

---

# 38. Open Decisions

| Decision                        | Status |
| ------------------------------- | ------ |
| ORM                             | TBD    |
| Migration tool                  | TBD    |
| Exact authentication data model | TBD    |
| Exact JSON schemas              | TBD    |
| Content version identity        | TBD    |
| RPS section-level traceability  | TBD    |
| Moodle object mapping           | TBD    |
| Data retention period           | TBD    |
| Secret storage mechanism        | TBD    |
| Student account provisioning    | TBD    |

---

# 39. Implementation Rules

Backend implementation harus mengikuti prinsip:

1. Gunakan relational columns untuk entity identity dan relationship.
2. Gunakan JSONB untuk structured-but-flexible data.
3. Jangan menyimpan credential pada agent tables.
4. Jangan menghapus generated versions secara otomatis.
5. Persist agent workflow state.
6. Persist operational events.
7. Simpan Moodle external IDs.
8. Gunakan foreign key untuk relationship utama.
9. Gunakan transaction untuk state transition internal.
10. Jangan menggabungkan database transaction dengan external Moodle API transaction seolah-olah keduanya atomic.

---

# 40. Data Model Status

**Status: Proposed**

Entity utama telah ditentukan pada level konseptual.

Detail berikut masih dapat berubah setelah dokumen berikut selesai:

* `agent-design.md`
* `content-schema.md`
* final Moodle capability mapping
* authentication design
* API implementation design

Perubahan schema harus dievaluasi terhadap PRD dan System Design sebelum implementation dikunci.

---

# 41. Related Documents

* `project-charter.md`
* `prd.md`
* `system-design.md`
* `api-specification.md`
* `moodle-integration.md`
* `agent-design.md`
* `content-schema.md`
* `testing-quality.md`
