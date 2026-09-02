# SYSTEM DESIGN

## Agentic AI untuk Mengisi Konten Moodle

**Project:** Capstone Project — Institut Teknologi Kalimantan (ITK)
**Document:** System Design
**Version:** 0.1
**Status:** Draft
**Related Documents:**

* `project-charter.md`
* `prd.md`

---

# 1. Purpose

Dokumen ini mendefinisikan desain teknis tingkat sistem untuk **Agentic AI untuk Mengisi Konten Moodle**.

System Design menerjemahkan requirement produk menjadi rancangan teknis yang mencakup:

* system architecture;
* component architecture;
* agent architecture;
* data flow;
* RPS processing;
* content generation;
* validation;
* instructor review;
* Moodle integration;
* controlled tool layer;
* monitoring;
* authentication;
* data management;
* error handling; dan
* security boundary.

Dokumen ini tidak mengunci detail implementasi yang masih dalam tahap evaluasi seperti model LLM final, document processor final, atau Moodle Web Service function tertentu.

---

# 2. Design Goals

System harus dirancang untuk:

1. Mendukung workflow Agentic AI end-to-end.
2. Menjaga RPS sebagai sumber utama informasi akademik.
3. Memisahkan AI reasoning dari external system execution.
4. Menyediakan human-in-the-loop sebelum execution.
5. Mendukung generation konten satu semester.
6. Mendukung optional learning activities seperti assignment dan quiz.
7. Menyediakan monitoring terhadap proses agent.
8. Memungkinkan retry dan recovery terhadap kegagalan.
9. Mengisolasi dependency Moodle.
10. Memungkinkan perubahan model LLM tanpa perubahan besar terhadap sistem.
11. Menjaga credential Moodle dari akses langsung LLM.
12. Menjaga arsitektur tetap sederhana dan sesuai kebutuhan Capstone.

---

# 3. Design Principles

## 3.1 RPS as Source of Truth

RPS merupakan sumber utama informasi akademik.

System tidak boleh memperlakukan knowledge yang dihasilkan AI sebagai pengganti informasi akademik dari RPS.

---

## 3.2 Separation of Reasoning and Execution

AI bertanggung jawab terhadap reasoning dan decision-making dalam workflow yang diizinkan.

Backend dan controlled tool layer bertanggung jawab terhadap execution.

```text
AI / Agent
    ↓
Tool Request
    ↓
Controlled Tool Layer
    ↓
Backend
    ↓
External Service
```

Agent tidak melakukan operasi eksternal secara langsung.

---

## 3.3 Human-in-the-Loop

Instructor tetap memiliki kontrol terhadap hasil sebelum hasil dieksekusi ke Moodle.

```text
Generate
   ↓
Validate
   ↓
Review
   ↓
Approve
   ↓
Execute
```

---

## 3.4 Dependency Isolation

Komponen yang bergantung pada external service harus diisolasi.

Contoh:

```text
Agent Core
    ↓
Moodle Tool Interface
    ↓
Moodle Adapter
    ↓
Moodle Web Service API
```

Perubahan terhadap Moodle API tidak boleh memaksa perubahan pada core agent.

---

## 3.5 Structured Agent Output

Agent tidak menghasilkan output sebagai free-form text saja.

Output antar tahap harus memiliki struktur yang dapat:

* divalidasi;
* disimpan;
* diteruskan ke tahap berikutnya;
* ditampilkan pada UI;
* dan dieksekusi ke Moodle.

---

# 4. High-Level Architecture

Arsitektur sistem:

```text
┌───────────────────────────────────────────────┐
│                Web Application                │
│                                               │
│  Instructor UI       Agent Monitoring UI      │
│  Review UI            Course UI               │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│                  Backend API                   │
│                                               │
│ Authentication                                │
│ Workflow Management                            │
│ Course Management                              │
│ Review Management                              │
│ Agent Session Management                       │
│ Moodle Integration                             │
└───────────────┬─────────────────┬─────────────┘
                │                 │
                ▼                 ▼
┌──────────────────────┐   ┌────────────────────┐
│    Agent System      │   │     PostgreSQL     │
│                      │   │                    │
│ Supervisor / Planner │   │ Users              │
│ Analysis             │   │ Courses            │
│ Generation           │   │ RPS Data           │
│ Validation           │   │ Agent Runs         │
│ Retry / Fix          │   │ Generated Content  │
└──────────┬───────────┘   │ Review Data        │
           │               └────────────────────┘
           ▼
┌──────────────────────┐
│     LLM Runtime      │
│       Ollama         │
└──────────────────────┘

           Agent Tool Request
                    │
                    ▼
┌───────────────────────────────────────────────┐
│           Controlled Tool Layer               │
│                                               │
│ Moodle Tools                                  │
│ Validation Tools                              │
│ Content Tools                                 │
│ Other Approved Tools                          │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│             Moodle Service Adapter            │
└───────────────────────┬───────────────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────┐
│          Moodle Web Service API               │
│                                               │
│              Moodle LMS ITK                   │
└───────────────────────────────────────────────┘
```

---

# 5. Major Components

## 5.1 Web Application

Web Application merupakan client utama sistem.

Fungsi utama:

* authentication;
* RPS upload;
* Instructor Profile;
* Additional Prompt;
* activity configuration;
* course plan review;
* content review;
* regeneration;
* approval;
* agent monitoring;
* execution control;
* verification result.

Platform:

**Standard Web Application**

Custom Chromium bukan requirement sistem.

---

# 6. Backend

Backend menjadi orchestration layer antara client, agent, database, dan external service.

Tanggung jawab utama:

* authentication;
* authorization;
* request validation;
* workflow management;
* agent session management;
* data persistence;
* review state;
* execution control;
* Moodle integration;
* event generation;
* logging;
* error handling.

Backend tidak bertanggung jawab terhadap reasoning AI secara langsung.

---

# 7. Agent System

Agent System merupakan komponen utama yang menjalankan workflow Agentic AI.

Secara konseptual agent terdiri dari beberapa capability:

```text
Supervisor / Orchestrator
        │
        ├── RPS Analysis
        ├── Course Planning
        ├── Content Generation
        ├── Validation
        ├── Retry / Fix
        ├── Moodle Tool Usage
        └── Verification
```

Pembagian agent menjadi beberapa agent independen masih merupakan architectural decision yang dapat berubah setelah evaluasi implementasi.

Sistem tidak harus menggunakan banyak agent apabila satu orchestrator dengan modular capability sudah memenuhi kebutuhan.

---

# 8. Agent Workflow

Workflow utama:

```text
START
  │
  ▼
Process RPS
  │
  ▼
Analyze RPS
  │
  ▼
Build Course Plan
  │
  ▼
Instructor Review
  │
  ├── Reject ───────► Regenerate Plan
  │
  ▼
Generate Weekly Content
  │
  ▼
Validate Content
  │
  ├── Failed ───────► Retry / Fix
  │                       │
  │                       └── Failed repeatedly → Human Review
  │
  ▼
Instructor Review
  │
  ├── Reject ───────► Regenerate Content
  │
  ▼
Approve
  │
  ▼
Execute to Moodle
  │
  ├── Failed ───────► Retry / Error Handling
  │
  ▼
Verify
  │
  ├── Failed ───────► Retry / Human Intervention
  │
  ▼
COMPLETED
```

---

# 9. Agent State Model

Agent workflow menggunakan state untuk merepresentasikan kondisi proses.

Contoh state:

```text
CREATED
PROCESSING_RPS
ANALYZING_RPS
PLANNING
WAITING_PLAN_REVIEW
GENERATING_CONTENT
VALIDATING
WAITING_CONTENT_REVIEW
APPROVED
EXECUTING
VERIFYING
RETRYING
FAILED
COMPLETED
```

State transition dikontrol oleh backend dan workflow engine, bukan hanya oleh LLM.

---

# 10. RPS Processing Pipeline

RPS Processing terdiri dari:

```text
RPS File
   ↓
Document Parsing
   ↓
Text Extraction
   ↓
Normalization
   ↓
Structured Representation
   ↓
RPS Analysis
```

Output processing minimal terdiri dari:

### Raw/Normalized Content

Representasi teks/Markdown yang mempertahankan informasi dokumen.

### Structured RPS Data

Data terstruktur yang merepresentasikan informasi akademik penting.

Contoh konseptual:

```json
{
  "course": {
    "name": "...",
    "code": "...",
    "credits": 3
  },
  "learning_outcomes": [],
  "topics": [],
  "weekly_plan": [],
  "assessment": [],
  "references": []
}
```

Schema final ditentukan pada tahap implementation/design detail.

---

# 11. RPS Analysis

RPS Analysis bertujuan mengubah structured RPS menjadi informasi yang dapat digunakan agent.

Informasi yang dapat dianalisis:

* course identity;
* learning outcomes;
* objectives;
* topics;
* weekly distribution;
* learning methods;
* assessments;
* references;
* prerequisites;
* relevant academic constraints.

Hasil analysis harus mempertahankan traceability terhadap sumber informasi.

---

# 12. Instructor Context

Agent menerima tiga sumber konteks utama:

```text
RPS
 +
Instructor Profile
 +
Additional Prompt
```

Prioritas konteks:

```text
Academic Constraints / RPS
        ↓
System Constraints
        ↓
Instructor Profile
        ↓
Additional Prompt
```

Apabila terdapat konflik, system harus menerapkan aturan precedence yang telah ditentukan.

Instructor Profile dan Additional Prompt tidak boleh menghapus constraint akademik yang berasal dari RPS.

---

# 13. Course Planning

Course Planner menghasilkan struktur course berdasarkan RPS.

Output konseptual:

```text
Course
│
├── Week 1
│   ├── Topic
│   ├── Learning Objective
│   └── Activities
│
├── Week 2
│   ├── Topic
│   ├── Learning Objective
│   └── Activities
│
├── ...
│
└── Week 16
    ├── Topic
    ├── Learning Objective
    └── Activities
```

Jumlah minggu mengikuti struktur RPS.

16 minggu merupakan target utama MVP, bukan constraint bahwa setiap course harus selalu memiliki tepat 16 minggu.

---

# 14. Content Generation

Content Generator menghasilkan konten berdasarkan Course Plan.

Input:

```text
RPS Analysis
+
Course Plan
+
Instructor Profile
+
Additional Prompt
+
Activity Configuration
```

Output dapat mencakup:

* learning material;
* learning resources;
* assignment;
* quiz;
* aktivitas lain yang secara eksplisit didukung sistem.

Activity Configuration menentukan tipe aktivitas yang boleh dihasilkan.

---

# 15. Activity Configuration

Instructor dapat menentukan tipe aktivitas yang ingin dibuat.

Contoh:

```json
{
  "learning_material": true,
  "assignment": true,
  "quiz": false
}
```

Agent harus mengikuti konfigurasi tersebut.

Jika `assignment = false`, agent tidak boleh menghasilkan assignment sebagai bagian dari workflow yang ditentukan.

Jika `quiz = false`, agent tidak boleh menghasilkan quiz.

---

# 16. Content Representation

Generated content harus memiliki structured representation sebelum execution.

Contoh konseptual:

```json
{
  "week": 1,
  "topic": "...",
  "learning_objectives": [],
  "materials": [],
  "resources": [],
  "activities": {
    "assignment": null,
    "quiz": null
  }
}
```

Struktur final akan disesuaikan dengan Moodle execution requirements.

---

# 17. Validation Layer

Validation dilakukan sebelum hasil masuk ke execution.

Validation mencakup:

### RPS Validation

Memastikan konten sesuai dengan informasi RPS.

### Structural Validation

Memastikan output memiliki struktur yang valid.

### Configuration Validation

Memastikan aktivitas mengikuti pilihan instructor.

### Consistency Validation

Memastikan tidak terdapat konflik yang tidak diinginkan antar bagian course.

### Execution Validation

Memastikan output memiliki informasi yang dibutuhkan untuk Moodle execution.

---

# 18. Retry and Fix

Ketika validation gagal:

```text
Generate
   ↓
Validate
   ↓
Failed
   ↓
Identify Failure
   ↓
Fix / Regenerate
   ↓
Validate Again
```

Retry tidak boleh dilakukan tanpa batas.

System harus memiliki batas retry yang dapat dikonfigurasi.

Jika retry tetap gagal:

```text
Retry Limit Reached
        ↓
Human Review
        ↓
Instructor Decision
```

---

# 19. Instructor Review

Review dilakukan pada dua tahap utama:

### Course Plan Review

Instructor memeriksa struktur course sebelum content generation dilanjutkan.

### Content Review

Instructor memeriksa konten sebelum execution ke Moodle.

Instructor dapat:

* approve;
* reject;
* edit;
* regenerate;
* memberikan instruction tambahan.

---

# 20. Moodle Integration Architecture

Moodle integration menggunakan abstraction:

```text
Agent
  ↓
Tool Interface
  ↓
Moodle Tool
  ↓
Moodle Service Adapter
  ↓
Moodle Web Service API
  ↓
Moodle LMS ITK
```

Agent tidak mengetahui detail authentication atau credential Moodle.

Agent hanya mengetahui tool yang tersedia.

---

# 21. Controlled Tool Layer

Controlled Tool Layer merupakan security dan execution boundary antara agent dan external service.

Contoh tool:

```text
Moodle Tools
├── Course Tools
├── Section Tools
├── Material Tools
├── Assignment Tools
├── Quiz Tools
├── User/Role Tools
└── Verification Tools
```

Tool yang tersedia ditentukan oleh backend.

Agent tidak dapat membuat tool baru atau melakukan arbitrary API request.

---

# 22. Moodle Operations

System membutuhkan kemampuan untuk melakukan operasi terkait:

### Course

* menentukan target course;
* membaca informasi course;
* membuat atau memperbarui course jika diperlukan dalam scope;
* membaca course state.

### Weekly Sections

* membuat atau memperbarui section;
* menentukan urutan minggu;
* membaca section state.

### Learning Materials

* membuat atau memperbarui materi;
* menempatkan materi pada section yang sesuai;
* membaca hasil execution.

### Assignment

Jika diaktifkan:

* membuat assignment;
* mengatur parameter yang diperlukan;
* menempatkan assignment pada minggu yang sesuai;
* melakukan verification.

### Quiz

Jika diaktifkan:

* membuat quiz;
* mengatur parameter yang diperlukan;
* menempatkan quiz pada minggu yang sesuai;
* melakukan verification.

### Student Access

* memastikan student role/account dapat mengakses course;
* mendukung verification dari perspektif student.

Detail Moodle Web Service function belum dikunci dalam System Design ini dan akan ditentukan berdasarkan capability Moodle ITK.

---

# 23. Moodle Authentication

Authentication ke Moodle dilakukan oleh integration layer.

Credential/token:

```text
Moodle Credential
       ↓
Backend / Secure Configuration
       ↓
Moodle Adapter
       ↓
Moodle Web Service
```

Credential tidak:

* dikirim ke LLM;
* dimasukkan ke prompt;
* disimpan dalam agent context;
* ditampilkan pada monitoring UI.

Mekanisme authentication final mengikuti konfigurasi Moodle ITK.

---

# 24. Database Design

Database digunakan untuk menyimpan state dan data yang dibutuhkan sistem.

Entity utama secara konseptual:

```text
User
 │
 ├── Instructor Profile
 │
 └── Agent Run
        │
        ├── RPS
        ├── Course Plan
        ├── Generated Content
        ├── Validation Result
        ├── Review
        ├── Execution
        └── Verification
```

Entity konseptual:

### User

Menyimpan identitas dan role pengguna aplikasi.

### Instructor Profile

Menyimpan preferensi instructor.

### RPS

Menyimpan metadata dan representation RPS.

### Course

Merepresentasikan project/course yang sedang diproses.

### Course Plan

Menyimpan hasil planning.

### Content

Menyimpan generated content.

### Activity

Menyimpan aktivitas seperti assignment atau quiz.

### Agent Run

Merepresentasikan satu execution workflow agent.

### Agent Event

Menyimpan event/status yang digunakan monitoring.

### Validation Result

Menyimpan hasil validation.

### Review

Menyimpan action dan keputusan instructor.

### Moodle Execution

Menyimpan hasil operasi terhadap Moodle.

### Verification

Menyimpan hasil verification.

---

# 25. Conceptual Data Relationship

```text
User
 │
 ├───────────────┐
 │               │
 ▼               ▼
Instructor     Agent Run
Profile          │
                 ├── RPS
                 ├── Course Plan
                 ├── Content
                 ├── Validation
                 ├── Review
                 ├── Execution
                 ├── Verification
                 └── Events
```

Detail relational schema ditentukan pada database design tahap berikutnya.

---

# 26. Monitoring Architecture

Monitoring digunakan untuk memberikan visibility terhadap workflow agent.

```text
Agent / Backend
      │
      │ Events
      ▼
Event / State Store
      │
      ▼
WebSocket / Real-Time Channel
      │
      ▼
Monitoring UI
```

Monitoring tidak mengambil state langsung dari LLM.

Backend menjadi source of truth untuk agent state.

---

# 27. Monitoring Events

Event yang dapat ditampilkan:

```text
RPS_PROCESSING_STARTED
RPS_PROCESSING_COMPLETED
RPS_ANALYSIS_STARTED
RPS_ANALYSIS_COMPLETED
PLANNING_STARTED
PLANNING_COMPLETED
VALIDATION_STARTED
VALIDATION_FAILED
RETRY_STARTED
CONTENT_GENERATION_STARTED
CONTENT_GENERATION_COMPLETED
REVIEW_REQUIRED
APPROVED
MOODLE_EXECUTION_STARTED
MOODLE_EXECUTION_COMPLETED
MOODLE_EXECUTION_FAILED
VERIFICATION_STARTED
VERIFICATION_COMPLETED
WORKFLOW_COMPLETED
WORKFLOW_FAILED
```

Event schema final ditentukan pada implementation design.

---

# 28. Monitoring UI

Monitoring UI minimal menampilkan:

* current workflow stage;
* overall status;
* current task;
* progress;
* event history;
* validation result;
* execution status;
* error;
* retry status;
* completion status.

UI tidak perlu menampilkan internal chain-of-thought LLM.

Monitoring menampilkan **operational events dan status**, bukan private reasoning model.

---

# 29. API Layer

Backend menyediakan API untuk client dan internal system.

Kelompok endpoint konseptual:

```text
/auth
/users
/instructors
/rps
/courses
/course-plans
/content
/agent-runs
/reviews
/execution
/verification
/monitoring
```

Endpoint dan payload final ditentukan pada API specification.

---

# 30. Long-Running Workflow

Generation course satu semester dapat membutuhkan waktu lama.

Oleh karena itu workflow tidak dirancang sebagai satu synchronous HTTP request.

Konseptual:

```text
Client
  │
  │ Start Workflow
  ▼
Backend
  │
  │ Create Agent Run
  ▼
Background Agent Execution
  │
  ├── Processing
  ├── Planning
  ├── Generation
  ├── Validation
  └── Execution
        │
        ▼
Event / State Update
        │
        ▼
Monitoring UI
```

Client dapat meninggalkan halaman tanpa menyebabkan workflow kehilangan state.

---

# 31. Error Handling

Error dibagi menjadi beberapa kategori:

### Validation Error

Output agent tidak memenuhi validation criteria.

Action:

```text
Validation Error
→ Retry/Fix
→ Validation
→ Human Review if necessary
```

### LLM Error

LLM gagal menghasilkan output.

Action:

```text
LLM Error
→ Retry
→ Fallback / Human Intervention
```

### Moodle Error

Moodle API gagal.

Action:

```text
Moodle Error
→ Capture Error
→ Retry if Safe
→ Human Intervention
```

### System Error

Backend atau infrastructure failure.

Action:

```text
System Error
→ Persist State
→ Log Error
→ Recovery / Restart
```

---

# 32. Idempotency

Moodle execution harus mempertimbangkan kemungkinan retry.

System harus menghindari kondisi seperti:

```text
First Execution
→ Material Created

Retry
→ Same Material Created Again
```

Apabila memungkinkan, system harus menggunakan identifier atau state tracking untuk menentukan apakah object Moodle sudah berhasil dibuat.

---

# 33. Security Architecture

Security boundary utama:

```text
                TRUST BOUNDARY

┌─────────────────────────────────────┐
│ Backend / Controlled Tool Layer     │
│                                     │
│ Moodle Credential                   │
│ Authentication                      │
│ Authorization                       │
│ API Execution                       │
└──────────────────┬──────────────────┘
                   │
                   │ Controlled Operation
                   ▼
              Moodle API


┌─────────────────────────────────────┐
│ Agent / LLM                         │
│                                     │
│ Reasoning                           │
│ Planning                            │
│ Generation                          │
│ Validation                          │
└─────────────────────────────────────┘

LLM tidak memiliki akses langsung
ke Moodle Credential.
```

---

# 34. Authorization

Application harus membedakan role:

```text
Instructor
    ├── Upload RPS
    ├── Generate
    ├── Review
    ├── Approve
    ├── Execute
    └── Monitor

Student
    └── Access Result / Course
```

Student tidak memiliki akses terhadap:

* Instructor Profile management;
* generation;
* agent execution;
* Moodle credential;
* review;
* approval.

---

# 35. LLM Runtime

Local LLM dijalankan melalui Ollama sebagai proposed runtime.

Arsitektur:

```text
Agent
  ↓
LLM Interface
  ↓
Ollama
  ↓
Selected LLM Model
```

Agent tidak boleh bergantung langsung pada API model tertentu.

Dengan abstraction tersebut, model dapat diganti tanpa mengubah keseluruhan agent workflow.

Model final belum ditentukan.

---

# 36. LLM Model Evaluation

Model akan dievaluasi berdasarkan:

1. Instruction following.
2. Bahasa Indonesia.
3. Reasoning.
4. Structured output.
5. Tool calling.
6. RPS adherence.
7. Content quality.
8. Latency.
9. Resource requirements.
10. Reliability.

Model final dipilih berdasarkan hasil evaluasi dan kemampuan hardware yang tersedia.

---

# 37. Document Processing

Document processing bertanggung jawab terhadap:

* file ingestion;
* text extraction;
* structure preservation;
* normalization;
* conversion ke representation yang dapat diproses AI.

Docling merupakan candidate solution.

Pipeline harus dirancang agar document processor dapat diganti apabila evaluasi menunjukkan solusi lain lebih sesuai.

---

# 38. Data Flow End-to-End

```text
                 Instructor
                     │
                     ▼
                 Upload RPS
                     │
                     ▼
              RPS Processing
                     │
                     ▼
                RPS Analysis
                     │
             ┌───────┴───────┐
             │               │
             ▼               ▼
     Instructor Profile   Additional Prompt
             │               │
             └───────┬───────┘
                     ▼
              Course Planning
                     │
                     ▼
             Instructor Review
                     │
                     ▼
          Weekly Content Generation
                     │
                     ▼
                Validation
                     │
              ┌──────┴──────┐
              │             │
            Failed        Passed
              │             │
              ▼             ▼
           Retry/Fix     Instructor Review
                            │
                            ▼
                          Approve
                            │
                            ▼
                    Controlled Tool Layer
                            │
                            ▼
                     Moodle Adapter
                            │
                            ▼
                    Moodle Web Service
                            │
                            ▼
                      Moodle LMS ITK
                            │
                            ▼
                       Verification
                            │
                            ▼
                       Student View
```

---

# 39. Failure Boundaries

Setiap major stage harus memiliki failure boundary.

```text
RPS Processing
      ↓
RPS Analysis
      ↓
Planning
      ↓
Generation
      ↓
Validation
      ↓
Review
      ↓
Execution
      ↓
Verification
```

Failure pada satu tahap harus memiliki state yang jelas sehingga proses dapat:

* retry;
* resume;
* regenerate;
* atau diteruskan kepada human intervention.

---

# 40. Observability

System harus menyediakan observability pada level:

### Agent

* state;
* event;
* duration;
* retry;
* validation result.

### Backend

* request;
* error;
* workflow;
* execution.

### Moodle

* operation;
* success/failure;
* response/error;
* execution identifier apabila tersedia.

Sensitive information tidak boleh dimasukkan ke log.

---

# 41. Technology Direction

| Component            | Technology                  | Status    |
| -------------------- | --------------------------- | --------- |
| Frontend             | React + TypeScript          | Proposed  |
| Backend              | FastAPI + Python            | Proposed  |
| Database             | PostgreSQL                  | Proposed  |
| LLM Runtime          | Ollama                      | Proposed  |
| LLM Model            | Selected through evaluation | TBD       |
| Document Processing  | Docling                     | Candidate |
| Representation       | Markdown + Structured JSON  | Proposed  |
| Real-Time Monitoring | WebSocket / equivalent      | Proposed  |
| Client               | Standard Web Application    | Confirmed |
| Moodle               | Moodle LMS ITK              | Confirmed |
| Moodle Integration   | Moodle Web Service API      | Confirmed |

---

# 42. Architecture Decisions

Keputusan arsitektur utama:

### AD-001 — Standard Web Application

System menggunakan standard web application dan tidak bergantung pada custom Chromium.

### AD-002 — Controlled Moodle Access

Agent tidak diberikan akses langsung ke Moodle credential/API.

### AD-003 — Moodle Adapter

Moodle integration diisolasi melalui adapter/tool layer.

### AD-004 — Human Review

Instructor review ditempatkan sebelum Moodle execution.

### AD-005 — Structured Agent Output

Output agent menggunakan structured representation.

### AD-006 — Backend as State Authority

Backend menjadi source of truth untuk workflow state.

### AD-007 — Local LLM Runtime

LLM dijalankan secara local melalui Ollama sebagai technology direction.

---

# 43. Open Technical Decisions

Hal-hal yang masih membutuhkan evaluasi atau keputusan:

1. LLM model final.
2. Agent orchestration pattern final.
3. Apakah menggunakan single agent dengan tools atau beberapa specialized agents.
4. Document processor final.
5. Exact Moodle Web Service functions.
6. Moodle authentication configuration.
7. Moodle capability/permission requirements.
8. Final database schema.
9. Exact API specification.
10. Retry strategy.
11. Maximum retry count.
12. Exact validation scoring mechanism.
13. Event schema.
14. WebSocket implementation details.
15. Content schema yang paling sesuai dengan Moodle.

---

# 44. Design Constraints

1. System harus dapat dijalankan dengan hardware yang tersedia.
2. Local LLM memiliki keterbatasan resource.
3. Moodle integration dibatasi oleh capability Web Service pada Moodle ITK.
4. Agent tidak boleh mendapatkan credential Moodle secara langsung.
5. Human review harus tetap tersedia sebelum execution.
6. Arsitektur harus tetap sederhana dan proporsional terhadap kebutuhan Capstone.
7. Custom Chromium tidak menjadi dependency sistem.

---

# 45. Future Extension

Architecture harus memungkinkan pengembangan lebih lanjut tanpa menjadi dependency MVP.

Potential future extensions:

* additional Moodle activities;
* additional document formats;
* additional LLM models;
* richer instructor personalization;
* advanced analytics;
* more sophisticated agent planning;
* additional LMS integration;
* automated quality scoring.

Fitur tersebut tidak menjadi bagian dari MVP kecuali secara eksplisit ditambahkan melalui perubahan scope.

---

# 46. Traceability

System Design harus dapat ditelusuri ke requirement pada PRD.

Contoh:

| PRD Requirement               | System Design Component         |
| ----------------------------- | ------------------------------- |
| FR-004 RPS Upload             | RPS Processing Pipeline         |
| FR-006 RPS Analysis           | RPS Analysis                    |
| FR-008 Instructor Profile     | Instructor Context              |
| FR-014 Course Planning        | Course Planning                 |
| FR-020 Weekly Content         | Content Generation              |
| FR-025 Activity Configuration | Activity Configuration          |
| FR-032 Validation             | Validation Layer                |
| FR-033 Retry/Fix              | Retry and Fix                   |
| FR-042 Instructor Review      | Instructor Review               |
| FR-047 Moodle Integration     | Moodle Integration Architecture |
| FR-057 Monitoring             | Monitoring Architecture         |
| FR-064 Student Perspective    | Student Verification            |
| NFR-007 Credential Protection | Security Architecture           |
| NFR-016 Agent Logging         | Observability                   |

---

# 47. Implementation Boundary

System Design ini tidak menetapkan secara final:

* source code structure;
* class structure;
* exact database columns;
* exact API payload;
* exact Moodle endpoint/function;
* exact LLM model;
* exact prompt;
* deployment topology;
* infrastructure provider.

Detail tersebut ditentukan pada implementation design atau technical specification setelah keputusan yang diperlukan tersedia.

---

# 48. Document Status

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| Document     | System Design                          |
| Project      | Agentic AI untuk Mengisi Konten Moodle |
| Version      | 0.1                                    |
| Status       | Draft                                  |
| Owner        | Project Team                           |
| Last Updated | 2026-09-02                             |

## Version History

| Version | Date       | Description           | Author       |
| ------- | ---------- | --------------------- | ------------ |
| 0.1     | 2026-09-02 | Initial System Design | Project Team |
