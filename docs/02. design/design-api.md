# API SPECIFICATION

## Agentic AI untuk Mengisi Konten Moodle

**Project:** Capstone Project — Institut Teknologi Kalimantan (ITK)
**Document:** API Specification
**Version:** 0.5
**Status:** Draft
**Related Documents:**

* `project-charter.md`
* `prd.md`
* `system-design.md`

---

# 1. Purpose

Dokumen ini mendefinisikan kontrak API tingkat aplikasi antara Web Application dan Backend.

API bertanggung jawab untuk:

* authentication;
* RPS management;
* course management;
* course planning;
* content generation;
* validation;
* instructor review;
* regeneration;
* Moodle execution;
* verification;
* agent monitoring.

API tidak mengekspos Moodle Web Service API secara langsung kepada frontend.

---

# 2. API Architecture

```text
Web Application
      │
      │ Application API
      ▼
Backend API
      │
      ├── Agent System
      │
      ├── PostgreSQL
      │
      └── Moodle Integration
              │
              ▼
       Moodle Web Service API
```

Frontend hanya berkomunikasi dengan Backend API.

Agent juga tidak memanggil Moodle API secara langsung.

---

# 3. API Principles

API mengikuti prinsip:

1. Frontend tidak mengakses Moodle secara langsung.
2. Agent tidak mengakses Moodle credential secara langsung.
3. Backend menjadi authority untuk workflow state.
4. Long-running workflow menggunakan asynchronous execution.
5. API harus mengembalikan status yang jelas.
6. Error harus dapat ditangani oleh client.
7. Resource memiliki identifier yang konsisten.
8. Operasi yang dapat menyebabkan duplicate execution harus mempertimbangkan idempotency.
9. Sensitive information tidak boleh dikembalikan ke client tanpa kebutuhan.
10. Detail Moodle Web Service function diisolasi di integration layer.

---

# 4. Base URL

Development:

```text
/api/v1
```

Production base URL ditentukan pada deployment configuration.

---

# 5. Authentication

## 5.1 Login

```http
POST /api/v1/auth/login
```

Request:

```json
{
  "username": "string",
  "password": "string"
}
```

Response:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": "string",
    "role": "instructor"
  }
}
```

---

## 5.2 Current User

```http
GET /api/v1/auth/me
```

Response:

```json
{
  "id": "string",
  "name": "string",
  "email": "string",
  "role": "instructor"
}
```

---

# 6. RPS API

## 6.1 Upload RPS

```http
POST /api/v1/rps
```

Content-Type:

```text
multipart/form-data
```

Request:

```text
file: PDF/DOCX
```

Response:

```json
{
  "id": "rps_001",
  "filename": "rps.pdf",
  "status": "uploaded"
}
```

---

## 6.2 Get RPS

```http
GET /api/v1/rps/{rps_id}
```

Response:

```json
{
  "id": "rps_001",
  "filename": "rps.pdf",
  "status": "processed",
  "created_at": "datetime"
}
```

---

## 6.3 Process RPS

```http
POST /api/v1/rps/{rps_id}/process
```

Response:

```json
{
  "rps_id": "rps_001",
  "status": "processing",
  "agent_run_id": "run_001"
}
```

Processing merupakan asynchronous operation.

---

## 6.4 Get RPS Analysis

```http
GET /api/v1/rps/{rps_id}/analysis
```

Mengembalikan hasil RPS Analysis yang tersimpan pada `rps.structured_data` sesuai Content Schema §6–§7 (DL-006, DL-009). Endpoint ini membaca data tersimpan dan tidak menjalankan document processing maupun analisis ulang.

Response:

```json
{
  "rps_id": "rps_001",
  "status": "analyzed",
  "schema_version": "1.0",
  "course": {},
  "cpl": [],
  "cpmk": [],
  "sub_cpmk": [],
  "study_materials": [],
  "weekly_plan": [],
  "assessments": [],
  "references": {},
  "media": {},
  "extraction": {}
}
```

Error:

* `RESOURCE_NOT_FOUND` apabila RPS tidak ditemukan.
* `INVALID_REQUEST` apabila RPS belum selesai dianalisis.

## 6.5 Catatan Pemrosesan

Endpoint `GET /api/v1/rps/{rps_id}/structured-data` digabungkan ke §6.4 (DL-009).

Catatan: `POST /api/v1/rps/{rps_id}/process` memulai Workflow untuk RPS tersebut dan mengembalikan `workflow_id`. Docling hanya dijalankan apabila dokumen belum pernah diproses dengan `file_hash` dan `schema_version` yang sama.

## 6.6 List RPS

```http
GET /api/v1/rps
```

Mengembalikan daftar RPS milik dosen yang login.

```json
{
  "items": [
    {
      "id": "rps_001",
      "filename": "rps.pdf",
      "status": "analyzed",
      "workflow_id": "wf_001",
      "uploaded_at": "datetime"
    }
  ]
}
```

Status dokumen RPS: `uploaded`, `processing`, `processed`, `analyzing`, `analyzed`, `failed`.

## 6.7 Reanalyze RPS

```http
POST /api/v1/rps/{rps_id}/reanalyze
```

Menjalankan RPS Analysis ulang dari `source_document` tanpa menjalankan Docling kembali. Digunakan ketika analisis sebelumnya gagal atau dosen meminta analisis ulang.

```json
{
  "rps_id": "rps_001",
  "status": "analyzing",
  "workflow_id": "wf_001"
}
```

---

# 7. Instructor Setup API

Instructor Setup mengikuti Proposal §3.3.2 dan §3.4.2: Instructor Profile, Additional Prompt, dan Activity Configuration dikelola per dosen dan diambil serta disimpan dalam satu alur.

## 7.1 Get Instructor Setup

```http
GET /api/v1/instructors/me/setup
```

Response:

```json
{
  "instructor_profile": {
    "teaching_style": "string",
    "expertise": "string",
    "delivery_preference": "string"
  },
  "additional_prompt": "string",
  "activity_configuration": {
    "learning_material": true,
    "learning_resource": true,
    "assignment": false,
    "quiz": false
  }
}
```

## 7.2 Update Instructor Setup

```http
PUT /api/v1/instructors/me/setup
```

Request menggunakan struktur yang sama dengan response §7.1.

Validasi:

* `additional_prompt` tidak melebihi batas panjang yang dikonfigurasi;
* minimal satu jenis konten pada `activity_configuration` bernilai `true`;
* hanya role `DOSEN` yang dapat mengakses endpoint ini.

Error validasi menggunakan `INVALID_REQUEST` dengan detail per field.

Instructor Setup merupakan konteks pendukung dan tidak menggantikan informasi akademik dari RPS.

---

# 8. Course API

Catatan (DL-011): pada implementasi, satu proses pembuatan course direpresentasikan oleh Workflow (§15). Endpoint berbasis `/courses/{course_id}` pada §8–§14 diselaraskan menjadi `/workflows/{workflow_id}/...` saat tahap terkait diimplementasikan. Activity Configuration dikelola per dosen melalui Instructor Setup (§7).

## 8.1 Create Generation Project

```http
POST /api/v1/courses
```

Request:

```json
{
  "rps_id": "rps_001",
  "moodle_course_id": "string",
  "additional_prompt": "string",
  "activity_configuration": {
    "learning_material": true,
    "assignment": true,
    "quiz": false
  }
}
```

Response:

```json
{
  "id": "course_project_001",
  "status": "created"
}
```

---

## 8.2 Get Course Project

```http
GET /api/v1/courses/{course_id}
```

---

## 8.3 Update Activity Configuration

```http
PUT /api/v1/courses/{course_id}/activity-configuration
```

Request:

```json
{
  "learning_material": true,
  "assignment": true,
  "quiz": false
}
```

---

# 9. Course Planning API

## 9.1 Generate Course Plan

```http
POST /api/v1/courses/{course_id}/plan
```

Response:

```json
{
  "course_id": "course_project_001",
  "agent_run_id": "run_002",
  "status": "planning"
}
```

---

## 9.2 Get Course Plan

```http
GET /api/v1/courses/{course_id}/plan
```

Response:

```json
{
  "id": "plan_001",
  "course_id": "course_project_001",
  "weeks": []
}
```

---

## 9.3 Approve Course Plan

```http
POST /api/v1/courses/{course_id}/plan/approve
```

Response:

```json
{
  "course_id": "course_project_001",
  "status": "approved"
}
```

---

## 9.4 Regenerate Course Plan

```http
POST /api/v1/courses/{course_id}/plan/regenerate
```

Request:

```json
{
  "instruction": "Perbaiki pembagian materi minggu 5-8"
}
```

Response:

```json
{
  "agent_run_id": "run_003",
  "status": "regenerating"
}
```

---

# 10. Content API

## 10.1 Generate Content

```http
POST /api/v1/courses/{course_id}/content/generate
```

Request:

```json
{
  "weeks": "all"
}
```

Response:

```json
{
  "agent_run_id": "run_004",
  "status": "generating"
}
```

---

## 10.2 Generate Specific Weeks

```http
POST /api/v1/courses/{course_id}/content/generate
```

Request:

```json
{
  "weeks": [1, 2, 3]
}
```

Hal ini memungkinkan regeneration atau generation parsial tanpa mengulang seluruh semester.

---

## 10.3 Get Generated Content

```http
GET /api/v1/courses/{course_id}/content
```

Optional query:

```text
?week=1
```

Response:

```json
{
  "course_id": "course_project_001",
  "weeks": [
    {
      "week": 1,
      "topic": "string",
      "learning_objectives": [],
      "materials": [],
      "resources": [],
      "activities": {
        "assignment": null,
        "quiz": null
      }
    }
  ]
}
```

---

## 10.4 Regenerate Content

```http
POST /api/v1/courses/{course_id}/content/{content_id}/regenerate
```

Request:

```json
{
  "instruction": "Perjelas contoh pada bagian kedua."
}
```

Response:

```json
{
  "agent_run_id": "run_005",
  "status": "regenerating"
}
```

---

# 11. Validation API

## 11.1 Validate Content

```http
POST /api/v1/courses/{course_id}/validation
```

Response:

```json
{
  "validation_id": "validation_001",
  "status": "completed",
  "result": "passed",
  "issues": []
}
```

---

## 11.2 Get Validation Result

```http
GET /api/v1/courses/{course_id}/validation
```

Response:

```json
{
  "validation_id": "validation_001",
  "result": "failed",
  "issues": [
    {
      "type": "rps_adherence",
      "severity": "medium",
      "message": "..."
    }
  ]
}
```

---

# 12. Review API

## 12.1 Get Reviewable Content

```http
GET /api/v1/courses/{course_id}/review
```

Response:

```json
{
  "course_id": "course_project_001",
  "status": "waiting_review",
  "items": []
}
```

---

## 12.2 Approve Content

```http
POST /api/v1/courses/{course_id}/review/approve
```

Response:

```json
{
  "course_id": "course_project_001",
  "status": "approved"
}
```

---

## 12.3 Reject Content

```http
POST /api/v1/courses/{course_id}/review/reject
```

Request:

```json
{
  "reason": "Materi minggu 4 tidak sesuai dengan RPS."
}
```

---

# 13. Moodle Execution API

## 13.1 Execute Course

```http
POST /api/v1/courses/{course_id}/execute
```

Response:

```json
{
  "execution_id": "execution_001",
  "status": "queued"
}
```

Execution merupakan asynchronous operation.

---

## 13.2 Get Execution Status

```http
GET /api/v1/courses/{course_id}/execution/{execution_id}
```

Response:

```json
{
  "execution_id": "execution_001",
  "status": "completed",
  "completed_items": 42,
  "failed_items": 0
}
```

---

## 13.3 Cancel Execution

```http
POST /api/v1/courses/{course_id}/execution/{execution_id}/cancel
```

Cancellation hanya dapat dilakukan pada state yang memungkinkan.

## 13.4 Moodle Integration Endpoints (Internal)

Endpoint berikut digunakan untuk memeriksa koneksi dan menguji operasi Moodle Integration Layer. Endpoint tidak menerima maupun mengembalikan credential Moodle.

```http
GET  /api/v1/integrations/moodle/status
GET  /api/v1/integrations/moodle/courses
GET  /api/v1/integrations/moodle/courses/{moodle_course_id}
GET  /api/v1/integrations/moodle/courses/{moodle_course_id}/contents
POST /api/v1/integrations/moodle/courses
POST /api/v1/integrations/moodle/courses/{moodle_course_id}/sections
```

| Endpoint                | Kegunaan                                                         | Akses                    |
| ----------------------- | ---------------------------------------------------------------- | ------------------------ |
| `status`                | Status koneksi, versi Moodle, dan ketersediaan functions yang dibutuhkan | Dosen               |
| `GET courses`           | Daftar course Moodle untuk dipilih sebagai course target (Proposal §3.4.7) | Dosen             |
| `courses/{id}`          | Membaca informasi course                                         | Dosen                    |
| `courses/{id}/contents` | Membaca section dan module course                                | Dosen                    |
| `POST courses`          | Membuat course untuk pengujian integrasi                         | Development environment  |
| `POST .../sections`     | Membuat atau memperbarui section untuk pengujian integrasi       | Development environment  |

Endpoint write hanya aktif pada development environment melalui konfigurasi. Eksekusi ke Moodle pada alur produk tetap melalui Moodle Execution API (§13.1).

---

# 14. Verification API

## 14.1 Start Verification

```http
POST /api/v1/courses/{course_id}/verification
```

Response:

```json
{
  "verification_id": "verification_001",
  "status": "running"
}
```

---

## 14.2 Get Verification Result

```http
GET /api/v1/courses/{course_id}/verification/{verification_id}
```

Response:

```json
{
  "verification_id": "verification_001",
  "status": "completed",
  "result": "passed",
  "checks": []
}
```

---

# 15. Workflow API

Workflow merepresentasikan satu proses pembuatan course dari RPS hingga verifikasi, sesuai class diagram proposal (Workflow, WorkflowEvent) dan DL-011.

## 15.1 List Workflows

```http
GET /api/v1/workflows
```

Mengembalikan daftar workflow milik dosen yang login.

## 15.2 Get Workflow

```http
GET /api/v1/workflows/{workflow_id}
```

Response:

```json
{
  "id": "wf_001",
  "rps_id": "rps_001",
  "status": "ANALYZING_RPS",
  "moodle_course_id": 12,
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

## 15.3 Get Workflow Events

```http
GET /api/v1/workflows/{workflow_id}/events
```

Response:

```json
{
  "items": [
    {
      "id": "evt_001",
      "event_type": "PERUBAHAN_TAHAP",
      "stage": "PROCESSING_RPS",
      "message": "Pemrosesan dokumen RPS dimulai",
      "timestamp": "datetime"
    }
  ]
}
```

`event_type`: `PERUBAHAN_TAHAP`, `AKTIVITAS_AGENT`, `OPERASI_MOODLE`, `RETRY_FIX`, `ERROR_FAILURE`.

## 15.4 Set Moodle Course Target

```http
PUT /api/v1/workflows/{workflow_id}/moodle-target
```

Request:

```json
{
  "moodle_course_id": 12
}
```

Menyimpan course target Moodle yang dipilih dosen dari `GET /api/v1/integrations/moodle/courses` (Proposal §3.4.7).

---

# 16. Monitoring

Monitoring menggunakan Workflow API (§15) untuk initial state dan riwayat, serta WebSocket (§17) untuk pembaruan real-time. Monitoring tidak menampilkan reasoning internal model.

---

# 17. WebSocket Monitoring

```text
WS /api/v1/ws/workflows/{workflow_id}
```

Koneksi diautentikasi menggunakan token pengguna. Hanya dosen pemilik workflow yang dapat berlangganan.

Event example:

```json
{
  "workflow_id": "wf_001",
  "event_type": "PERUBAHAN_TAHAP",
  "stage": "ANALYZING_RPS",
  "status": "ANALYZING_RPS",
  "message": "Analisis RPS dimulai",
  "timestamp": "datetime"
}
```

Event tidak memuat credential, API key, maupun isi prompt.

Frontend harus mengambil initial state melalui HTTP sebelum menggunakan event stream agar tidak bergantung pada event yang terjadi sebelum koneksi dibuat.

---

# 18. API Error Format

Semua API menggunakan struktur error yang konsisten.

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Content validation failed.",
    "details": []
  }
}
```

Contoh error codes:

```text
AUTHENTICATION_FAILED
AUTHORIZATION_DENIED
RESOURCE_NOT_FOUND
INVALID_REQUEST
INVALID_FILE
RPS_PROCESSING_FAILED
LLM_GENERATION_FAILED
VALIDATION_FAILED
REVIEW_REQUIRED
EXECUTION_FAILED
MOODLE_ERROR
VERIFICATION_FAILED
WORKFLOW_FAILED
INTERNAL_ERROR
```

---

# 19. HTTP Status Codes

| Status | Usage                          |
| ------ | ------------------------------ |
| 200    | Successful request             |
| 201    | Resource successfully created  |
| 202    | Async operation accepted       |
| 400    | Invalid request                |
| 401    | Authentication required/failed |
| 403    | Insufficient permission        |
| 404    | Resource not found             |
| 409    | Resource/state conflict        |
| 422    | Validation error               |
| 500    | Internal server error          |
| 502    | External service failure       |
| 504    | External service timeout       |

---

# 20. Workflow State API Contract

Backend harus menjaga state transition.

Status workflow mengikuti `WorkflowStatus` pada proposal (DL-011):

```text
PROCESSING_RPS
   ↓
ANALYZING_RPS
   ↓
PLANNING_COURSE
   ↓
VALIDATING
   ↓
WAITING_FOR_REVIEW
   ↓
GENERATING_CONTENT
   ↓
VALIDATING
   ↓
WAITING_FOR_REVIEW
   ↓
EXECUTING_TO_MOODLE
   ↓
VERIFYING
   ↓
COMPLETED
```

Status `RETRYING` dan `FAILED` dapat terjadi pada setiap tahap.

Tidak semua state dapat dipanggil secara bebas oleh client.

Contoh:

```text
WAITING_FOR_REVIEW
        ↓
     APPROVE
        ↓
EXECUTING_TO_MOODLE (setelah dosen menjalankan eksekusi)
```

Client tidak boleh langsung mengubah state menjadi `COMPLETED`.

---

# 21. Idempotency

Operation berikut harus mempertimbangkan idempotency:

* Moodle execution;
* content generation;
* regeneration;
* verification.

Client dapat mengirim:

```http
Idempotency-Key: <unique-key>
```

untuk operation yang mendukung idempotency.

Implementasi final ditentukan pada backend design.

---

# 22. Authorization Matrix

| Operation                    | Dosen | Mahasiswa |
| ---------------------------- | ----: | --------: |
| Upload RPS                   |   Yes |        No |
| Process / Reanalyze RPS      |   Yes |        No |
| View RPS Analysis            |   Yes |        No |
| Manage Instructor Setup      |   Yes |        No |
| Select Moodle Course Target  |   Yes |        No |
| Generate Course Plan         |   Yes |        No |
| Review Course Plan           |   Yes |        No |
| Generate Content             |   Yes |        No |
| Review Content               |   Yes |        No |
| Approve Content              |   Yes |        No |
| Execute to Moodle            |   Yes |        No |
| Monitor Workflow             |   Yes |        No |
| View Verification Result     |   Yes |        No |
| Submit Student Verification  |    No |       Yes |
| View Student Verification    |   Yes |        No |
| Access Result Course         |   Yes |       Yes |

Role mengikuti enumeration `Role` pada proposal: `DOSEN` dan `MAHASISWA` (DL-011).

---

# 23. API Security Requirements

1. Semua authenticated endpoint harus memerlukan authentication.
2. Authorization harus dilakukan pada backend.
3. Instructor hanya dapat mengakses resource yang diizinkan.
4. Student tidak dapat menjalankan generation atau execution.
5. Moodle credential tidak boleh dikembalikan melalui API.
6. Sensitive data tidak boleh dimasukkan ke response atau monitoring event.
7. API harus melakukan input validation.
8. File upload harus divalidasi berdasarkan type dan size.
9. Error response tidak boleh membocorkan internal implementation details.

---

# 24. Async Operations

Operation berikut harus menggunakan asynchronous workflow:

* RPS processing;
* RPS analysis apabila membutuhkan processing panjang;
* course planning;
* content generation;
* validation;
* Moodle execution;
* verification.

Pattern:

```text
POST request
    ↓
Create Agent Run
    ↓
Return 202
    ↓
Background Processing
    ↓
Update State
    ↓
Emit Event
    ↓
Client Monitoring
```

---

# 25. API and Moodle Separation

Frontend:

```text
Frontend
   ↓
Application API
   ↓
Backend
   ↓
Moodle Adapter
   ↓
Moodle Web Service API
```

Frontend tidak boleh:

```text
Frontend
   ↓
Moodle Web Service API
```

Agent juga tidak boleh:

```text
Agent
   ↓
Moodle Web Service API
```

Pemisahan ini menjaga credential, authorization, validation, dan execution policy tetap berada di backend.

---

# 26. Moodle API Mapping

Mapping antara Application API dan Moodle Web Service function dilakukan pada integration layer.

Contoh konseptual:

| Application Operation       | Moodle Function | Status |
| --------------------------- | --------------- | ------ |
| Create/Update Course        | TBD             | TBD    |
| Create/Update Section       | TBD             | TBD    |
| Create Material             | TBD             | TBD    |
| Create Assignment           | TBD             | TBD    |
| Create Quiz                 | TBD             | TBD    |
| Student Access Verification | TBD             | TBD    |

Nama function Moodle tidak ditentukan dalam dokumen ini sebelum dilakukan API capability mapping terhadap instance Moodle tim (lihat DL-003).

---

# 27. API Versioning

API menggunakan version prefix:

```text
/api/v1
```

Breaking changes harus menggunakan version baru.

Contoh:

```text
/api/v1
/api/v2
```

Minor changes yang backward-compatible tidak membutuhkan version baru.

---

# 28. Open API Decisions

Hal yang masih perlu ditentukan:

1. Authentication mechanism aplikasi.
2. Token/session strategy.
3. Exact request/response schema.
4. Pagination strategy.
5. File size limits.
6. API rate limiting.
7. Background job mechanism.
8. WebSocket authentication.
9. Idempotency implementation.
10. Exact Moodle Web Service mapping.
11. Moodle authentication configuration.
12. Error mapping dari Moodle ke application error.
13. API documentation format.

---

# 29. Traceability

| Requirement | API Component              |
| ----------- | -------------------------- |
| FR-004      | RPS API                    |
| FR-008      | Instructor Profile API     |
| FR-011      | Course API                 |
| FR-014      | Course Planning API        |
| FR-020      | Content API                |
| FR-025      | Activity Configuration API |
| FR-032      | Validation API             |
| FR-042      | Review API                 |
| FR-047      | Moodle Execution API       |
| FR-053      | Verification API           |
| FR-057      | Monitoring API             |
| NFR-007     | API Security               |
| NFR-016     | Agent Run / Monitoring API |

---

# 30. Document Control

| Field        | Value                                  |
| ------------ | -------------------------------------- |
| Document     | API Specification                      |
| Project      | Agentic AI untuk Mengisi Konten Moodle |
| Version      | 0.5                                    |
| Status       | Draft                                  |
| Owner        | Project Team                           |
| Last Updated | 2026-10-19                             |

## Version History

| Version | Date       | Description               | Author       |
| ------- | ---------- | ------------------------- | ------------ |
| 0.1     | 2026-09-02 | Initial API Specification | Project Team |
| 0.2     | 2026-10-13 | Referensi target Moodle disesuaikan dengan DL-001 dan DL-003 | Project Manager |
| 0.3     | 2026-10-13 | Penambahan endpoint RPS structured data (§6.5) dan Moodle integration internal (§13.4) | Project Manager |
| 0.4     | 2026-10-14 | §6.4 menjadi endpoint hasil RPS Analysis; §6.5 digabungkan (DL-009) | Project Manager |
| 0.5     | 2026-10-19 | Instructor Setup API, list/reanalyze RPS, Workflow API dan WebSocket, daftar course Moodle, authorization matrix (DL-011) | Project Manager |
