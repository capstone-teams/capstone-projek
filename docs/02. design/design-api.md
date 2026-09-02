# API SPECIFICATION

## Agentic AI untuk Mengisi Konten Moodle

**Project:** Capstone Project — Institut Teknologi Kalimantan (ITK)
**Document:** API Specification
**Version:** 0.1
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

Response:

```json
{
  "rps_id": "rps_001",
  "course": {
    "name": "string",
    "code": "string",
    "credits": 3
  },
  "learning_outcomes": [],
  "topics": [],
  "weekly_plan": [],
  "assessment": [],
  "references": []
}
```

---

# 7. Instructor Profile API

## 7.1 Get Profile

```http
GET /api/v1/instructors/me/profile
```

## 7.2 Update Profile

```http
PUT /api/v1/instructors/me/profile
```

Request:

```json
{
  "teaching_style": "string",
  "language_preference": "Bahasa Indonesia",
  "content_preference": "string"
}
```

Schema final ditentukan berdasarkan requirement profile.

---

# 8. Course API

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

# 15. Agent Run API

## 15.1 Get Agent Run

```http
GET /api/v1/agent-runs/{run_id}
```

Response:

```json
{
  "id": "run_001",
  "status": "running",
  "stage": "content_generation",
  "started_at": "datetime"
}
```

---

## 15.2 Get Agent Run History

```http
GET /api/v1/courses/{course_id}/agent-runs
```

Response:

```json
{
  "runs": [
    {
      "id": "run_001",
      "type": "rps_processing",
      "status": "completed"
    },
    {
      "id": "run_002",
      "type": "course_planning",
      "status": "completed"
    }
  ]
}
```

---

# 16. Monitoring API

## 16.1 Get Current Workflow Status

```http
GET /api/v1/courses/{course_id}/monitoring
```

Response:

```json
{
  "course_id": "course_project_001",
  "status": "generating_content",
  "stage": "week_5",
  "progress": {
    "completed": 4,
    "total": 16
  }
}
```

---

# 17. WebSocket Monitoring

HTTP API digunakan untuk initial state.

Real-time event menggunakan WebSocket.

```text
WS /api/v1/ws/courses/{course_id}
```

Event example:

```json
{
  "event": "CONTENT_GENERATION_STARTED",
  "course_id": "course_project_001",
  "week": 5,
  "timestamp": "datetime"
}
```

Event completion:

```json
{
  "event": "CONTENT_GENERATION_COMPLETED",
  "course_id": "course_project_001",
  "week": 5,
  "timestamp": "datetime"
}
```

Frontend harus melakukan initial state fetch melalui HTTP sebelum membuka atau menggunakan event stream agar tidak bergantung pada event yang terjadi sebelum connection dibuat.

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

Contoh:

```text
CREATED
   ↓
PROCESSING_RPS
   ↓
ANALYZING_RPS
   ↓
PLANNING
   ↓
WAITING_PLAN_REVIEW
   ↓
GENERATING_CONTENT
   ↓
VALIDATING
   ↓
WAITING_CONTENT_REVIEW
   ↓
APPROVED
   ↓
EXECUTING
   ↓
VERIFYING
   ↓
COMPLETED
```

Tidak semua state dapat dipanggil secara bebas oleh client.

Contoh:

```text
WAITING_CONTENT_REVIEW
        ↓
     APPROVE
        ↓
      APPROVED
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

| Operation                 | Instructor | Student |
| ------------------------- | ---------: | ------: |
| Upload RPS                |        Yes |      No |
| Process RPS               |        Yes |      No |
| View RPS Analysis         |        Yes |      No |
| Manage Instructor Profile |        Yes |      No |
| Generate Course Plan      |        Yes |      No |
| Review Course Plan        |        Yes |      No |
| Generate Content          |        Yes |      No |
| Review Content            |        Yes |      No |
| Approve Content           |        Yes |      No |
| Execute to Moodle         |        Yes |      No |
| Monitor Agent             |        Yes |      No |
| View Verification         |        Yes |      No |
| Access Result Course      |        Yes |     Yes |

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

Nama function Moodle tidak ditentukan dalam dokumen ini sebelum dilakukan API capability mapping terhadap environment Moodle ITK.

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
| Version      | 0.1                                    |
| Status       | Draft                                  |
| Owner        | Project Team                           |
| Last Updated | 2026-09-02                             |

## Version History

| Version | Date       | Description               | Author       |
| ------- | ---------- | ------------------------- | ------------ |
| 0.1     | 2026-09-02 | Initial API Specification | Project Team |
