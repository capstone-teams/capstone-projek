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

Field `username` berisi **identifier login**: username user atau email user.

Response:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "id": "string",
    "role": "INSTRUCTOR"
  }
}
```

Token adalah JWT `HS256` dengan masa berlaku `ACCESS_TOKEN_EXPIRE_MINUTES`
(default 30 menit). Role tidak menjadi klaim token; backend membacanya ulang
dari record User pada setiap request.

---

## 5.2 Current User

```http
GET /api/v1/auth/me
```

Response:

```json
{
  "id": "string",
  "username": "string",
  "firstname": "string",
  "lastname": "string",
  "email": "string",
  "role": "INSTRUCTOR"
}
```

Field identity mengikuti atribut user Moodle (`username`, `firstname`,
`lastname`, `email`). Nilai `role` adalah enum kanonik backend: `INSTRUCTOR`,
`STUDENT`, atau `ADMIN`.

Enum inilah yang **valid** dan yang tampil pada response login, `GET /auth/me`,
serta OpenAPI (BE-06.4). Proposal memakai istilah Indonesia pada class diagram;
padanannya satu-satu dan **tidak** menambah nilai baru:

| Proposal (class diagram) | Nilai kanonik API | Arti                      |
| ------------------------ | ----------------- | ------------------------- |
| `DOSEN`                  | `INSTRUCTOR`      | Dosen pengampu RPS         |
| `MAHASISWA`              | `STUDENT`         | Mahasiswa peserta mata kuliah |
| —                        | `ADMIN`           | Operasi administrasi       |

Frontend dan backend sama-sama memakai nilai kanonik tersebut; role tidak
pernah menjadi klaim token, sehingga perubahan role berlaku pada request
berikutnya tanpa menerbitkan token baru.

> Panduan integrasi lengkap — contoh request/response, format dan masa berlaku
> token, perilaku token kedaluwarsa, matriks role, serta daftar kode error —
> tersedia di
> [`auth-api-integration.md`](auth-api-integration.md) (BE-06.1). Dokumentasi
> OpenAPI interaktif tersedia pada `/docs` di environment development.

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
  "created_at": "datetime",
  "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ",
  "has_source_document": true,
  "processing_duration_ms": 8421,
  "processing_error_code": null,
  "processing_error_message": null
}
```

Endpoint ini juga menjadi **endpoint polling** untuk §6.3: setelah pemrosesan
dijadwalkan, client memantau `status` sampai bernilai `analyzed` atau `failed`.
`workflow_id` adalah workflow orkestrasi yang menjalankan pemrosesan dan
analisis dokumen ini (BE-11.2); event-nya dapat dipantau lewat §16 dan §17.
Dokumen yang belum pernah diproses sejak workflow diperkenalkan mengembalikan
`workflow_id` bernilai `null`.

Ketika `status` bernilai `failed`, `processing_error_code` memuat kode error §18
(mis. `RPS_PROCESSING_FAILED` untuk konversi, `LLM_GENERATION_FAILED` untuk
analisis) dan `processing_error_message` memuat alasan yang dapat dipahami
pengguna. Detail teknisnya tidak pernah dikembalikan, hanya dicatat server-side.

`source_document` (JSON hasil konversi) tidak dikembalikan pada response ini
karena ukurannya besar; ia tersedia bagi tahap ekstraksi (§6.4).

---

## 6.3 Process RPS

```http
POST /api/v1/rps/{rps_id}/process
```

Request body bersifat opsional:

```json
{
  "schema_version": "2.0"
}
```

`schema_version` boleh dikosongkan; bila diisi dan berbeda dari versi yang
tercatat pada dokumen, dokumen diproses ulang untuk versi skema tersebut.

Response `202 Accepted`:

```json
{
  "rps_id": "rps_001",
  "status": "processing",
  "schema_version": "2.0",
  "reused": false,
  "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ"
}
```

Processing merupakan asynchronous operation: request hanya **menjadwalkan**
pekerjaan, lalu pekerjaan itu berjalan di background. Sejak BE-11.2 pekerjaan
tersebut adalah satu workflow dengan dua tahap berurutan — `PROCESSING_RPS`
(konversi Docling, §6.3) lalu `ANALYZING_RPS` (analisis, §6.4/§6.6) — sehingga
client memantau `GET /api/v1/rps/{rps_id}` (§6.2) sampai statusnya `analyzed`
atau `failed`. `workflow_id` adalah workflow tersebut; status dan event-nya
tersedia pada §16 dan §17.

Bila dokumen sudah diproses untuk `file_hash` dan `schema_version` yang sama,
konversi tidak dijadwalkan ulang dan response-nya `200 OK` dengan
`"reused": true`. Workflow baru tetap dibuat agar tahap analisis yang belum
pernah berjalan dapat diselesaikan; `workflow_id` pada response menunjuk
workflow tersebut.

```json
{
  "rps_id": "rps_001",
  "status": "processed",
  "schema_version": "2.0",
  "reused": true,
  "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ"
}
```

Kegagalan tahap apa pun tidak muncul pada response ini (tidak ada client yang
menunggu pekerjaan background); kegagalannya terlihat pada §6.2 sebagai
`status: failed` beserta `processing_error_code` dan
`processing_error_message`, serta pada workflow (§16) sebagai `FAILED` dengan
event `WORKFLOW_FAILED`.

Field `agent_run_id` menyusul bersama Agent Run pada M03 (lihat §15) dan
karenanya belum ada pada response ini.

---

## 6.4 Get RPS Analysis

```http
GET /api/v1/rps/{rps_id}/analysis
```

Response:

```json
{
  "rps_id": "kP3nQ7vRtYx2bM8sLdWfZa",
  "analyzed_at": "2026-10-21T08:01:10Z",
  "data": {
    "schema_version": "2.0",
    "course": {
      "name": "Basis Data",
      "code": "IF123",
      "credits": 3
    },
    "cpmk": [],
    "sub_cpmk": [],
    "weeks": [],
    "assessments": [],
    "references": []
  }
}
```

`data` adalah **RPS Structured Data** utuh (content-schema §6.2 — identitas mata
kuliah, CPL, CPMK, Sub-CPMK, rencana mingguan, penilaian, referensi), bukan
ringkasan terpisah. Schema yang sama dipakai sebagai bentuk kolom
`rps.structured_data` (BE-08.2), sehingga client dan database tidak dapat
menyimpang.

Kode status: `200` bila RPS sudah dianalisis, `422 INVALID_REQUEST` bila
dokumen belum dianalisis, `404 RESOURCE_NOT_FOUND` bila RPS tidak ada, dan `403
AUTHORIZATION_DENIED` untuk RPS milik dosen lain atau akun mahasiswa.

## 6.5 Get RPS List

```http
GET /api/v1/rps
```

Response:

```json
{
  "items": [
    {
      "id": "kP3nQ7vRtYx2bM8sLdWfZa",
      "filename": "rps-basis-data.pdf",
      "status": "PROCESSED",
      "schema_version": "2.0",
      "workflow_id": null,
      "has_source_document": true,
      "created_at": "2026-10-21T08:00:00Z",
      "updated_at": "2026-10-21T08:00:42Z"
    }
  ]
}
```

Hanya RPS milik dosen yang login. `workflow_id` terisi setelah workflow
analisis dibuat (BE-11.2). Nilai `status` adalah enum kanonik backend: `UPLOADED`,
`PROCESSING`, `PROCESSED`, `FAILED` — dan `ANALYZING`, `ANALYZED` setelah BE-08.2
menambahkan tahap analisis. Nilai ditulis **huruf besar**, sama seperti response
endpoint RPS lainnya (§6.1–§6.3).

## 6.6 Reanalyze RPS

```http
POST /api/v1/rps/{rps_id}/reanalyze
```

Request tanpa body. Response `202 Accepted`:

```json
{
  "rps_id": "kP3nQ7vRtYx2bM8sLdWfZa",
  "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ",
  "status": "ANALYZING"
}
```

Analisis ulang berjalan dari `source_document` yang tersimpan — Docling tidak
dijalankan lagi — dan hanya boleh diminta dosen pemilik RPS. RPS yang sudah
berstatus `ANALYZED` tidak dianalisis ulang secara implisit; satu-satunya jalan
adalah endpoint ini. Client memantau hasilnya melalui §16/§17 lalu membaca
§6.4.

Sejak BE-11.2 analisis ulang dijalankan pada workflow yang sama dengan
pemrosesan sebelumnya: `workflow_id` yang dikembalikan adalah workflow yang
sudah tercatat pada RPS, dan event baru ditambahkan ke riwayat workflow tersebut
(§16.3). Dokumen yang dianalisis sebelum workflow diperkenalkan mendapat baris
workflow baru dengan id yang sudah tercatat pada RPS.

> **Status implementasi.** §6.4–§6.6 sudah terbit pada OpenAPI beserta contoh
> response dan seluruhnya sudah diimplementasikan: §6.6
> (`POST /api/v1/rps/{rps_id}/reanalyze`) bersama penyimpanan hasil analisis di
> `rps.structured_data` oleh BE-08.2, lalu §6.4 (`GET /rps/{rps_id}/analysis`)
> dan §6.5 (`GET /rps`) oleh BE-08.3. Kegagalan analisis terbaca pada §6.2
> sebagai `processing_error_code` (`LLM_GENERATION_FAILED`) +
> `processing_error_message`.

---

# 7. Instructor Setup API

Satu endpoint untuk seluruh setup dosen: preferensi mengajar, prompt tambahan,
dan konfigurasi aktivitas yang boleh dihasilkan agent. Dipakai agent pada semua
kursus milik dosen tersebut.

> Nama path kanonik adalah `/instructors/me/setup` (BE-10.2). Endpoint
> `/instructors/me/profile` pada versi dokumen sebelumnya **tidak** diterbitkan
> dan tidak pernah diimplementasikan; mock frontend yang masih memakainya
> diganti saat FE-07.2.

## 7.1 Get Setup

```http
GET /api/v1/instructors/me/setup
```

Response:

```json
{
  "instructor_profile": {
    "teaching_style": "Interaktif dengan studi kasus",
    "expertise": "Rekayasa Perangkat Lunak",
    "delivery_preference": "Materi ringkas, banyak contoh kode",
    "language_preference": "Bahasa Indonesia"
  },
  "additional_prompt": "Sertakan contoh SQL pada setiap materi.",
  "activity_configuration": {
    "learning_material": true,
    "learning_resource": true,
    "assignment": false,
    "quiz": false
  },
  "updated_at": "2026-10-21T08:02:00Z"
}
```

## 7.2 Update Setup

```http
PUT /api/v1/instructors/me/setup
```

Request — seluruh field opsional; hanya nilai yang dikirim yang diubah:

```json
{
  "instructor_profile": {
    "teaching_style": "string",
    "expertise": "string",
    "delivery_preference": "string",
    "language_preference": "Bahasa Indonesia"
  },
  "additional_prompt": "string",
  "activity_configuration": {
    "learning_material": true,
    "learning_resource": false,
    "assignment": false,
    "quiz": false
  }
}
```

Response sama dengan §7.1. Validasi (BE-10.2):

| Aturan                                    | Error                                     |
| ----------------------------------------- | ----------------------------------------- |
| `additional_prompt` melebihi batas panjang | `422 INVALID_REQUEST`, detail per field   |
| Tidak ada jenis aktivitas aktif (`true`)   | `422 INVALID_REQUEST`, detail per field   |
| Tipe data field salah                      | `422 INVALID_REQUEST`, detail per field   |
| Role bukan dosen                           | `403 AUTHORIZATION_DENIED`                |

Batas panjang `additional_prompt` dikonfigurasi melalui environment, sehingga
angkanya tidak di-hardcode pada kontrak ini.

Aturan pengosongan: nilai `null` pada field `instructor_profile` berarti "tidak
diubah"; `additional_prompt` dikosongkan dengan mengirim string kosong `""`.
Field yang tidak dikirim tidak berubah, dan body `{}` mengembalikan setup saat
ini tanpa menulis apa pun.

> **Status implementasi.** Kontrak terbit pada BE-06.4; endpoint aslinya
> tersedia sejak BE-10.2 dan stub `501 NOT_IMPLEMENTED` untuk §7 sudah dibuang.

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

# 16. Workflow Monitoring API

Workflow adalah satu rangkaian pekerjaan agent (analisis RPS, penyusunan
rencana, generasi konten, eksekusi Moodle). Semua endpoint di bawah hanya
menampilkan workflow milik dosen yang login.

## 16.1 Get Workflow List

```http
GET /api/v1/workflows
```

Response:

```json
{
  "items": [
    {
      "id": "q7RtYx2bM8sLdWfZaKp3nQ",
      "status": "RUNNING",
      "stage": "rps_analysis",
      "progress": {
        "completed": 1,
        "total": 4
      },
      "rps_id": "kP3nQ7vRtYx2bM8sLdWfZa",
      "created_at": "2026-10-21T08:03:00Z",
      "updated_at": "2026-10-21T08:03:20Z"
    }
  ]
}
```

Nilai `status` adalah enum: `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`
(huruf besar; BE-11.3).

## 16.2 Get Workflow Status

```http
GET /api/v1/workflows/{workflow_id}
```

Response sama dengan satu item §16.1 ditambah course target Moodle:

```json
{
  "id": "q7RtYx2bM8sLdWfZaKp3nQ",
  "status": "RUNNING",
  "stage": "rps_analysis",
  "progress": {
    "completed": 1,
    "total": 4
  },
  "rps_id": "kP3nQ7vRtYx2bM8sLdWfZa",
  "moodle_course_id": null,
  "created_at": "2026-10-21T08:03:00Z",
  "updated_at": "2026-10-21T08:03:20Z"
}
```

## 16.3 Get Workflow Event History

```http
GET /api/v1/workflows/{workflow_id}/events
```

Response memuat event dengan bentuk yang sama seperti frame WebSocket §17, urut
dari yang paling lama.

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

HTTP API (§16) digunakan untuk initial state; event real-time dikirim melalui
WebSocket berdasarkan `workflow_id`, bukan `course_id`.

```text
WS /api/v1/ws/workflows/{workflow_id}
```

Autentikasi memakai access token yang sama dengan HTTP (dikirim pada query
parameter `token` saat handshake, karena browser tidak dapat menyetel header
`Authorization` pada WebSocket). Workflow milik dosen lain ditolak saat
handshake.

Satu frame event:

```json
{
  "event": "WORKFLOW_STAGE_COMPLETED",
  "workflow_id": "q7RtYx2bM8sLdWfZaKp3nQ",
  "stage": "rps_analysis",
  "progress": {
    "completed": 2,
    "total": 4
  },
  "message": "Analisis RPS selesai.",
  "timestamp": "2026-10-21T08:03:30Z"
}
```

`event` memakai pola `WORKFLOW_*` (`WORKFLOW_STARTED`, `WORKFLOW_STAGE_STARTED`,
`WORKFLOW_STAGE_COMPLETED`, `WORKFLOW_COMPLETED`, `WORKFLOW_FAILED`). Bentuk
frame ini sama dengan item pada `GET /api/v1/workflows/{workflow_id}/events`
(§16.3) dan terbit pada OpenAPI sebagai schema `WorkflowEvent` — sehingga client
cukup memakai satu parser.

Event **tidak** memuat credential, API key, maupun isi prompt.

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
| 0.2     | 2026-10-21 | Kontrak Sprint 2 pada OpenAPI: enum role kanonik, RPS list/analysis/reanalyze, instructor setup, workflow & event WS (BE-06.4) | Project Team |
