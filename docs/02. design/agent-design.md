# Agent Design

## 1. Document Information

| Item              | Value                                                                      |
| ----------------- | -------------------------------------------------------------------------- |
| Document          | Agent Design                                                               |
| Project           | Agentic AI untuk Mengisi Konten Moodle                                     |
| Status            | Proposed                                                                   |
| Owner             | Capstone Team                                                              |
| Related Documents | Project Charter, PRD, System Design, Data Model, Moodle Integration Design |
| LLM Runtime       | Ollama — Proposed                                                          |
| Model             | TBD                                                                        |
| Architecture      | Single Orchestrator with Modular Capabilities — Proposed                   |

---

# 2. Purpose

Dokumen ini mendefinisikan desain Agentic AI yang digunakan untuk mengubah RPS menjadi course plan dan konten pembelajaran, melakukan validation, meminta instructor review, menjalankan operasi Moodle, dan melakukan verification.

Agent dirancang sebagai workflow yang memiliki kemampuan:

```text
Understand
   ↓
Plan
   ↓
Generate
   ↓
Validate
   ↓
Execute
   ↓
Verify
   ↓
Retry / Fix
```

Sistem tidak dianggap agentic hanya karena menggunakan LLM.

Agent harus memiliki:

* tujuan;
* state;
* workflow;
* tools;
* validation;
* execution;
* verification;
* recovery mechanism.

---

# 3. Agent Design Principles

## 3.1 LLM is Not the System

LLM merupakan reasoning/generation component.

LLM bukan:

* database;
* workflow state authority;
* authentication manager;
* Moodle client;
* permission manager.

Arsitektur:

```text
LLM
 ↓
Agent Orchestrator
 ↓
Backend
 ↓
Controlled Tools
```

---

## 3.2 Backend Controls Execution

Backend menentukan:

* workflow state;
* permission;
* available tools;
* tool arguments validation;
* persistence;
* retry;
* error handling.

LLM tidak memiliki authority untuk melakukan arbitrary system operation.

---

## 3.3 RPS Has Highest Academic Authority

Context hierarchy:

```text
Hard System Constraints
        ↓
Academic Constraints / RPS
        ↓
Instructor Profile
        ↓
Additional Prompt
        ↓
LLM Generation
```

Instructor Profile dan Additional Prompt tidak boleh digunakan untuk mengubah fakta akademik yang berasal dari RPS.

Contoh:

Jika RPS menetapkan 16 pertemuan, prompt tidak boleh membuat agent mengubahnya menjadi 20 hanya karena user meminta.

Jika terdapat konflik, agent harus:

```text
Detect conflict
 ↓
Report conflict
 ↓
Request instructor resolution
```

---

# 4. Agent Responsibilities

Agent bertanggung jawab terhadap:

1. memahami RPS;
2. menyusun course plan;
3. menghasilkan content;
4. mengikuti Instructor Profile;
5. mengikuti Additional Prompt;
6. melakukan self-validation;
7. menggunakan validation result;
8. menentukan kebutuhan retry/fix;
9. meminta human approval pada required checkpoint;
10. memilih tool yang tersedia;
11. menjalankan workflow;
12. melakukan verification.

Agent tidak bertanggung jawab langsung terhadap:

* credential storage;
* database transaction;
* raw Moodle HTTP request;
* user authentication;
* arbitrary code execution.

---

# 5. Agent Architecture

Recommended MVP architecture:

```text
                    ┌─────────────────────┐
                    │   Agent Orchestrator│
                    └──────────┬──────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
       RPS Analyzer       Planner          Content Generator
             │                 │                 │
             └─────────────────┼─────────────────┘
                               │
                               ▼
                         Validator
                               │
                               ▼
                         Tool Manager
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
         Internal Tools                 Moodle Tools
                                              │
                                              ▼
                                      Moodle Integration
```

Arsitektur ini menggunakan **single orchestrator dengan modular capabilities**.

Multi-agent bukan requirement MVP.

---

# 6. Why Single Orchestrator

Untuk Capstone, single orchestrator lebih disarankan dibanding langsung menggunakan banyak autonomous agents.

### Single Orchestrator

Kelebihan:

* lebih sederhana;
* lebih mudah di-debug;
* state management lebih jelas;
* observability lebih mudah;
* kebutuhan resource lebih rendah;
* lebih mudah diuji;
* lebih sedikit communication overhead.

Kekurangan:

* orchestrator memiliki responsibility lebih besar;
* kompleksitas dapat meningkat jika workflow terlalu besar.

### Multi-Agent

Kelebihan:

* responsibility dapat dipisahkan;
* cocok untuk workflow yang sangat kompleks.

Kekurangan:

* orchestration lebih kompleks;
* context passing lebih sulit;
* debugging lebih sulit;
* evaluasi lebih sulit;
* latency dan resource usage dapat meningkat.

Untuk MVP, kompleksitas tambahan multi-agent belum justified.

---

# 7. Agent Workflow

Main workflow:

```text
CREATED
   ↓
PROCESSING_RPS
   ↓
ANALYZING_RPS
   ↓
PLANNING
   ↓
VALIDATING_PLAN
   ↓
WAITING_PLAN_REVIEW
   ↓
GENERATING_CONTENT
   ↓
VALIDATING_CONTENT
   ↓
WAITING_CONTENT_REVIEW
   ↓
EXECUTING
   ↓
VERIFYING
   ↓
COMPLETED
```

Failure/recovery:

```text
Any State
   ↓
Error
   ↓
Retryable?
 ┌───────┴────────┐
Yes               No
 │                 │
Retry              FAILED
 │
Fix/Retry
```

---

# 8. Agent State Machine

Recommended states:

```text
CREATED
PROCESSING_RPS
ANALYZING_RPS
PLANNING
VALIDATING_PLAN
WAITING_PLAN_REVIEW
GENERATING_CONTENT
VALIDATING_CONTENT
WAITING_CONTENT_REVIEW
APPROVED
EXECUTING
VERIFYING
RETRYING
FAILED
COMPLETED
```

State transition harus dilakukan oleh Backend/Orchestrator.

LLM tidak boleh secara bebas mengubah persisted workflow state.

---

# 9. State Definitions

## CREATED

Agent run dibuat tetapi belum dieksekusi.

---

## PROCESSING_RPS

Sistem:

* membaca file;
* mengekstrak content;
* melakukan normalization;
* menghasilkan Markdown/structured representation.

LLM belum melakukan generation utama.

---

## ANALYZING_RPS

LLM atau analysis pipeline menginterpretasikan structured RPS.

Output:

```text
Course identity
Learning outcomes
Objectives
Topics
Weekly distribution
Teaching methods
Assessment
References
```

---

## PLANNING

Agent membuat course plan berdasarkan RPS analysis.

Output:

```text
Course
 ├── Week 1
 ├── Week 2
 ├── ...
 └── Week N
```

---

## VALIDATING_PLAN

Course plan diperiksa.

Checks:

* RPS adherence;
* weekly structure;
* completeness;
* consistency;
* configuration compliance.

---

## WAITING_PLAN_REVIEW

Course plan menunggu instructor.

Possible actions:

```text
APPROVE
REJECT
REQUEST_REGENERATION
EDIT
```

---

## GENERATING_CONTENT

Agent menghasilkan content berdasarkan approved course plan.

Content dapat dihasilkan:

* per week;
* per content;
* batch tertentu.

MVP sebaiknya mendukung granular regeneration agar failure tidak menyebabkan seluruh semester dibuat ulang.

---

## VALIDATING_CONTENT

Content diperiksa terhadap:

* RPS;
* course plan;
* Instructor Profile;
* Additional Prompt;
* internal content schema;
* activity configuration.

---

## WAITING_CONTENT_REVIEW

Instructor melakukan review sebelum Moodle execution.

---

## EXECUTING

Approved content dikirim melalui Controlled Tool Layer.

Agent tidak melakukan raw Moodle API call.

---

## VERIFYING

Sistem membaca kembali Moodle dan membandingkan expected state dengan actual state.

---

## RETRYING

Sistem menjalankan recovery terhadap operation yang gagal.

Retry harus bounded.

---

## FAILED

Workflow berhenti karena error yang tidak dapat diselesaikan secara otomatis.

---

## COMPLETED

Execution dan verification berhasil.

---

# 10. Agent Input Context

Agent context terdiri dari beberapa layer.

```text
System Constraints
       +
RPS Analysis
       +
Instructor Profile
       +
Additional Prompt
       +
Course Plan
       +
Previous Validation
       ↓
Agent Context
```

Tidak semua context perlu dikirim ke setiap LLM call.

Context harus dibuat task-specific.

---

# 11. Context Management

Agent tidak seharusnya selalu mengirim seluruh RPS dan seluruh semester content ke setiap request.

Context dapat dibagi:

```text
Global Context
 ├── Course information
 ├── RPS constraints
 └── Instructor profile

Task Context
 ├── Current week
 ├── Current topic
 ├── Current objective
 └── Required output schema

Validation Context
 ├── Generated output
 ├── Relevant RPS constraints
 └── Validation rules
```

Tujuan:

* mengurangi token usage;
* mengurangi noise;
* meningkatkan instruction adherence;
* meningkatkan latency.

---

# 12. RPS Analysis

RPS analysis menghasilkan intermediate representation.

Contoh:

```json
{
  "course": {
    "name": "Basis Data",
    "code": "IF123"
  },
  "learning_outcomes": [],
  "topics": [],
  "weeks": [],
  "assessments": [],
  "references": []
}
```

Intermediate representation menjadi boundary antara document processing dan agent reasoning.

---

# 13. Course Planning

Course planner menggunakan:

```text
RPS Analysis
+
Instructor Profile
+
Additional Prompt
```

Output harus structured.

Contoh:

```json
{
  "course": {
    "title": "Basis Data"
  },
  "weeks": [
    {
      "week": 1,
      "topic": "Introduction",
      "objectives": [],
      "activities": []
    }
  ]
}
```

Exact schema akan ditentukan dalam `content-schema.md`.

---

# 14. Content Generation

Content generator menerima:

```text
Approved Course Plan Week
+
Relevant RPS Information
+
Instructor Profile
+
Additional Prompt
+
Activity Configuration
```

Output:

```text
Learning Material
Optional Assignment
Optional Quiz
```

Learning material merupakan baseline MVP.

Assignment dan quiz hanya dibuat jika enabled.

---

# 15. Instructor Profile

Instructor Profile dapat mempengaruhi:

* writing style;
* explanation depth;
* language;
* examples;
* pedagogical presentation;
* preferred structure.

Namun:

```text
Instructor Profile
       ↓
Presentation / Generation Style
```

bukan:

```text
Instructor Profile
       ↓
Change Academic Facts
```

---

# 16. Additional Prompt

Additional Prompt memberikan instruction tambahan.

Contoh:

```text
"Gunakan lebih banyak contoh kasus industri."
```

Agent dapat menggunakannya untuk presentation style/content enrichment selama tidak bertentangan dengan RPS.

Conflict handling:

```text
RPS constraint
      vs
Additional Prompt
      ↓
Detect conflict
      ↓
RPS takes precedence
      ↓
Report limitation
```

---

# 17. Tool Architecture

Tools dibagi menjadi:

```text
Internal Tools
Moodle Tools
Validation Tools
```

### Internal Tools

Contoh:

```text
get_rps_analysis()
get_course_plan()
save_generated_content()
get_instructor_profile()
```

### Validation Tools

```text
validate_rps_adherence()
validate_schema()
validate_consistency()
```

### Moodle Tools

```text
moodle.get_course()
moodle.create_course()
moodle.update_course()
moodle.get_course_contents()
moodle.create_section()
moodle.create_learning_material()
moodle.create_assignment()
moodle.create_quiz()
moodle.verify_course()
```

Actual Moodle capabilities remain dependent on `moodle-integration.md`.

---

# 18. Tool Calling Policy

LLM may request a tool.

Backend decides whether the tool call is allowed.

Flow:

```text
LLM requests tool
       ↓
Tool Manager
       ↓
Validate tool name
       ↓
Validate arguments
       ↓
Check authorization
       ↓
Execute tool
       ↓
Return normalized result
```

LLM cannot invoke arbitrary functions.

---

# 19. Tool Input Validation

Example:

```json
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

Backend validates:

* tool exists;
* required fields exist;
* types are correct;
* target belongs to current course;
* instructor approval exists;
* operation is allowed;
* current workflow state permits operation.

---

# 20. Tool Output Normalization

Raw Moodle response tidak langsung dikembalikan ke LLM jika tidak diperlukan.

Raw response:

```text
Moodle-specific response
```

dapat dinormalisasi menjadi:

```json
{
  "success": true,
  "object_id": "123",
  "operation": "create_learning_material"
}
```

Untuk error:

```json
{
  "success": false,
  "error_code": "MOODLE_PERMISSION_DENIED",
  "retryable": false
}
```

Hal ini mengurangi coupling agent terhadap Moodle implementation details.

---

# 21. Validation Architecture

Validation dilakukan pada beberapa level.

```text
Input Validation
      ↓
Schema Validation
      ↓
Semantic Validation
      ↓
RPS Validation
      ↓
Execution Readiness Validation
      ↓
Moodle Verification
```

---

# 22. Input Validation

Memastikan input tersedia.

Contoh:

```text
RPS exists
Course exists
Instructor context exists
Required configuration exists
```

---

# 23. Schema Validation

Memastikan output LLM sesuai schema.

Contoh:

```text
week.number → integer
title → string
learning_outcomes → array
content → string/object
```

Structured output wajib divalidasi sebelum digunakan.

---

# 24. Semantic Validation

Memeriksa kualitas dan konsistensi.

Contoh:

```text
Topic:
Database Normalization

Generated Content:
Introduction to Web Development
```

Schema mungkin valid, tetapi semantic validation gagal.

---

# 25. RPS Adherence Validation

Validator membandingkan output terhadap RPS.

Checks:

* topic consistency;
* learning outcome alignment;
* weekly distribution;
* assessment alignment;
* academic constraints.

---

# 26. Execution Readiness Validation

Sebelum Moodle execution:

```text
Approved?
       ↓
Schema valid?
       ↓
Required fields complete?
       ↓
Activity configuration respected?
       ↓
Moodle mapping available?
       ↓
Ready
```

Jika tidak:

```text
BLOCK EXECUTION
```

---

# 27. Validation Result

Validator menghasilkan:

```json
{
  "status": "FAILED",
  "errors": [
    {
      "type": "RPS_MISMATCH",
      "message": "Generated topic does not match planned topic."
    }
  ],
  "warnings": []
}
```

Status:

```text
PASS
PARTIAL
FAIL
```

---

# 28. Retry and Fix

Retry digunakan jika failure masih dapat diperbaiki.

Contoh:

```text
Generation
 ↓
Validation
 ↓
FAIL
 ↓
Analyze failure
 ↓
Generate correction
 ↓
Validate again
```

Bukan:

```text
FAIL
 ↓
Generate random output again
```

---

# 29. Retry Categories

### Generation Failure

Contoh:

```text
Invalid structured output
```

Action:

```text
Regenerate with schema correction
```

### Validation Failure

Contoh:

```text
Topic does not match RPS
```

Action:

```text
Provide validation feedback
→ Regenerate
```

### Moodle Failure

Contoh:

```text
Timeout
```

Action:

```text
Retry execution if safe
```

### Permission Failure

Action:

```text
Do not retry automatically
```

---

# 30. Retry Limits

Retry harus bounded.

Example policy:

```text
MAX_GENERATION_RETRY = TBD
MAX_MOODLE_RETRY = TBD
```

Jika maximum retry tercapai:

```text
FAILED
```

dan instructor/operator mendapatkan informasi yang relevan.

Nilai final retry limit akan ditentukan melalui testing.

---

# 31. Human-in-the-Loop

Instructor review merupakan bagian dari system design, bukan failure state.

Minimum checkpoints:

```text
Course Plan
     ↓
Instructor Approval
     ↓
Content Generation
     ↓
Instructor Approval
     ↓
Moodle Execution
```

Tujuan:

* menjaga academic correctness;
* mengurangi hallucination impact;
* memberikan control;
* mencegah autonomous publishing yang tidak diinginkan.

---

# 32. Regeneration Granularity

Sistem harus mendukung regeneration pada level:

```text
Entire Course Plan
Entire Week
Single Content
Single Activity
```

Recommended MVP:

```text
Course Plan
Week
Single Content
```

Activity-level regeneration dapat ditambahkan jika implementasinya tidak meningkatkan kompleksitas secara signifikan.

---

# 33. Agent Memory

Agent tidak membutuhkan long-term autonomous memory sebagai requirement MVP.

Persistent context disimpan melalui application database:

```text
RPS
Instructor Profile
Course Plan
Content
Validation
Agent Run
Agent Events
```

Jika model membutuhkan previous output:

```text
Database
 ↓
Relevant context retrieval
 ↓
LLM
```

Bukan mengandalkan process memory.

---

# 34. Agent Run

Satu AgentRun merepresentasikan satu workflow execution.

Contoh:

```text
AgentRun #001
Type: COURSE_PLAN_GENERATION

AgentRun #002
Type: WEEK_CONTENT_GENERATION

AgentRun #003
Type: MOODLE_EXECUTION
```

AgentRun menyimpan:

* workflow type;
* model;
* state;
* retry count;
* timestamps;
* references.

---

# 35. Agent Events

Operational event example:

```text
RPS_PROCESSING_STARTED
RPS_PROCESSING_COMPLETED
ANALYSIS_STARTED
ANALYSIS_COMPLETED
PLANNING_STARTED
PLAN_GENERATED
PLAN_VALIDATION_FAILED
PLAN_REGENERATION_STARTED
PLAN_APPROVED
CONTENT_GENERATION_STARTED
CONTENT_GENERATED
CONTENT_VALIDATED
CONTENT_APPROVED
MOODLE_EXECUTION_STARTED
MOODLE_OPERATION_COMPLETED
VERIFICATION_STARTED
VERIFICATION_COMPLETED
WORKFLOW_COMPLETED
```

Events digunakan untuk monitoring.

---

# 36. Monitoring

Monitoring UI harus dapat menjawab:

```text
What is the agent doing?
What stage is active?
What has completed?
What failed?
What is waiting for instructor?
What will happen next?
```

Contoh:

```text
Course Generation
────────────────────────
✓ RPS Processing
✓ RPS Analysis
✓ Course Planning
✓ Plan Validation
✓ Instructor Approval
● Content Generation
○ Content Validation
○ Content Review
○ Moodle Execution
○ Verification
```

---

# 37. Reasoning Transparency

Monitoring tidak menampilkan hidden chain-of-thought.

Yang ditampilkan adalah operational explanation:

```text
"Generating Week 5 learning material based on
approved course plan and RPS objectives."
```

Bukan internal reasoning lengkap model.

---

# 38. Model Abstraction

LLM access harus melalui abstraction.

```text
Agent
 ↓
LLM Provider Interface
 ↓
Ollama Adapter
 ↓
Selected Model
```

Contoh:

```text
ILLMProvider
      │
      └── OllamaProvider
```

Tujuannya agar model dapat diganti tanpa mengubah seluruh agent architecture.

---

# 39. Model Evaluation

Model final masih TBD.

Candidate awal dapat dievaluasi berdasarkan:

| Criterion             | Importance |
| --------------------- | ---------- |
| Instruction following | High       |
| Bahasa Indonesia      | High       |
| RPS adherence         | Very High  |
| Structured output     | Very High  |
| Reasoning             | High       |
| Tool calling          | High       |
| Content quality       | Very High  |
| Latency               | Medium     |
| Hardware requirement  | High       |

Model dipilih berdasarkan hasil benchmark terhadap use case proyek, bukan semata-mata popularitas model.

---

# 40. Prompt Architecture

Prompt sebaiknya dipisahkan menjadi:

```text
System Instructions
+
Task Instructions
+
RPS Context
+
Instructor Profile
+
Additional Prompt
+
Output Schema
```

Contoh:

```text
SYSTEM
You are an educational content planning agent...

TASK
Create a course plan...

RPS
...

INSTRUCTOR PROFILE
...

ADDITIONAL PROMPT
...

OUTPUT SCHEMA
...
```

Prompt tidak boleh memberikan Moodle credential atau secret.

---

# 41. Structured Output

Agent generation harus menggunakan structured output jika didukung oleh model/runtime.

Tujuan:

* predictable parsing;
* schema validation;
* database persistence;
* tool calling;
* error recovery.

Free-form text tidak boleh menjadi contract utama antar-component.

---

# 42. Agent Security

Agent harus memiliki:

* least privilege;
* tool allowlist;
* input validation;
* output validation;
* credential isolation;
* execution approval;
* audit logging.

Tidak boleh:

```text
LLM → arbitrary shell
LLM → arbitrary HTTP
LLM → database credentials
LLM → Moodle credentials
```

---

# 43. Prompt Injection Consideration

RPS dan Additional Prompt merupakan input yang tidak sepenuhnya trusted.

Contoh RPS dapat mengandung teks seperti:

```text
Ignore previous instructions...
```

Agent harus memperlakukan dokumen sebagai **data**, bukan system instruction.

Hierarchy:

```text
System instruction
    >
Application rules
    >
RPS data
    >
Instructor preferences
    >
Additional user content
```

RPS content tidak boleh mengubah system/tool policy.

---

# 44. Hallucination Control

Hallucination mitigation:

1. RPS-first context.
2. Structured intermediate representation.
3. Explicit constraints.
4. Validation.
5. Instructor review.
6. Limited tool access.
7. Verification.
8. Retry/fix.

Target bukan mengklaim hallucination = 0%.

Target adalah membuat hallucination:

```text
Detectable
Recoverable
Controllable
```

---

# 45. Agent Failure Handling

Failure flow:

```text
Agent Step
    ↓
Failure
    ↓
Classify Failure
    ├── Recoverable
    │      ↓
    │    Retry/Fix
    │
    ├── Human Action Required
    │      ↓
    │    WAITING
    │
    └── Non-Recoverable
           ↓
         FAILED
```

---

# 46. Human Action Required

Examples:

```text
RPS conflict
Moodle permission missing
Ambiguous academic information
Content repeatedly fails validation
```

Agent should not silently guess when the decision materially affects academic content or external execution.

---

# 47. Agent Autonomy Boundary

Agent autonomous:

* analyze;
* plan;
* generate;
* validate;
* request tools;
* retry safe operations.

Human-controlled:

* approve course plan;
* approve generated content;
* authorize Moodle execution where required;
* resolve academic ambiguity;
* resolve permission/configuration issues.

Backend-controlled:

* credential;
* authorization;
* state;
* persistence;
* tool execution;
* external API communication.

---

# 48. End-to-End Agent Example

```text
1. Instructor uploads RPS
        ↓
2. Backend processes document
        ↓
3. Agent analyzes RPS
        ↓
4. Agent generates course plan
        ↓
5. Validator checks course plan
        ↓
6. Instructor approves
        ↓
7. Agent generates weekly content
        ↓
8. Validator checks content
        ↓
9. Instructor approves
        ↓
10. Agent requests Moodle tool
        ↓
11. Backend validates tool request
        ↓
12. Moodle Integration executes operation
        ↓
13. Backend records execution
        ↓
14. Verification reads Moodle
        ↓
15. Expected vs Actual comparison
        ↓
16. PASS
        ↓
17. Workflow completed
```

---

# 49. Agent Design and Data Model Relationship

Agent Design depends on:

```text
AgentRun
AgentEvent
ValidationResult
Review
MoodleExecution
Verification
```

Data flow:

```text
Agent
 ↓
AgentRun
 ↓
AgentEvent
 ↓
Generated Entity
 ↓
ValidationResult
 ↓
Review
 ↓
MoodleExecution
 ↓
Verification
```

Database remains persistent authority.

---

# 50. Agent Design and API Relationship

Frontend does not communicate directly with the agent runtime.

```text
Frontend
   ↓
Application Backend API
   ↓
Agent Orchestrator
   ↓
LLM / Tools
```

This allows:

* authentication;
* authorization;
* workflow management;
* persistence;
* monitoring;
* API consistency.

---

# 51. MVP Agent Boundary

MVP agent wajib mendukung:

* RPS analysis;
* course planning;
* weekly content generation;
* validation;
* instructor review;
* controlled tool calling;
* Moodle execution;
* verification;
* retry/fix;
* workflow monitoring.

MVP tidak wajib mendukung:

* multi-agent collaboration;
* autonomous long-term memory;
* autonomous course management;
* unrestricted tool generation;
* arbitrary code execution;
* autonomous publishing without approval.

---

# 52. Open Technical Decisions

| Decision                         | Status               |
| -------------------------------- | -------------------- |
| Final LLM model                  | TBD                  |
| Exact Ollama model configuration | TBD                  |
| Agent framework                  | TBD                  |
| Structured output mechanism      | TBD                  |
| Exact validation scoring         | TBD                  |
| Retry limits                     | TBD                  |
| Context window strategy          | TBD                  |
| Prompt templates                 | TBD                  |
| Tool calling format              | TBD                  |
| State persistence implementation | Proposed             |
| Multi-agent architecture         | Not required for MVP |
| Long-term agent memory           | Out of MVP           |

---

# 53. Definition of Done

Agent architecture dianggap siap untuk implementation apabila:

1. State machine telah diimplementasikan.
2. AgentRun dapat dipersist.
3. AgentEvent dapat direkam.
4. LLM provider dapat diganti melalui abstraction.
5. Output LLM memiliki schema.
6. Validation dapat dijalankan.
7. Retry memiliki limit.
8. Tool allowlist diterapkan.
9. Credential tidak masuk LLM context.
10. Instructor review menjadi workflow checkpoint.
11. Moodle execution melalui controlled tool layer.
12. Verification dilakukan setelah execution.
13. Failure dapat diklasifikasikan.
14. Monitoring dapat membaca workflow state.

---

# 54. Final Agent Architecture

```text
┌─────────────────────────────────────────────────┐
│                   Web App                       │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│             Application Backend API             │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│               Agent Orchestrator                │
│                                                 │
│ Understand → Plan → Generate → Validate         │
│ → Execute → Verify → Retry/Fix                  │
└───────┬──────────────────────┬──────────────────┘
        │                      │
        ▼                      ▼
┌───────────────┐      ┌─────────────────────┐
│ LLM Provider  │      │ Validation Engine   │
│               │      │                     │
│ Ollama        │      │ RPS / Schema /      │
│ Model = TBD   │      │ Semantic / Readiness│
└───────────────┘      └─────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────┐
│               Controlled Tool Layer             │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│             Moodle Integration Layer            │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│              Moodle Web Service API             │
└───────────────────────┬─────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────┐
│                  Moodle LMS ITK                 │
└─────────────────────────────────────────────────┘

                  ┌─────────────────┐
                  │   PostgreSQL    │
                  │                 │
                  │ AgentRun        │
                  │ AgentEvent      │
                  │ Validation      │
                  │ Review          │
                  │ Execution       │
                  │ Verification    │
                  └─────────────────┘
```

---

# 55. Document Status

**Status: Proposed**

Core agent architecture telah ditentukan pada level system design.

Detail berikut masih harus ditentukan melalui implementation/testing:

* final LLM;
* exact prompt;
* exact output schema;
* validation scoring;
* retry limit;
* agent framework;
* tool-calling implementation;
* context optimization.

Perubahan pada workflow utama harus dievaluasi terhadap PRD, System Design, dan Data Model.
