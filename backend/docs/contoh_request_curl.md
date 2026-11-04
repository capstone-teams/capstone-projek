# Contoh Request (curl)

Semua contoh memakai `BASE` yang sama. Untuk development lokal:

```bash
export BASE=http://localhost:8000
# server thinkpad lewat tunnel:
# export BASE=https://columns-possess-tourist-costumes.trycloudflare.com
```

Status endpoint per dokumen ini:

- ✅ **live** — sudah diimplementasikan hari ini.
- 🚧 **kontrak** — path dan body sudah ditetapkan di `design-api.md`, tetapi backend
  belum punya route-nya, sehingga sekarang menghasilkan `404 {"detail":"Not Found"}`.

Isi data contoh: `backend/scripts/seed_sample_course.py`
(atau `uv run python -m scripts.seed_sample_course --reset` di server).

---

## 0. Login & token

```bash
curl -s -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"username":"dosen.demo","password":"<password-akun-uji>"}' | tee /tmp/login.json

export TOKEN=$(python3 -c "import json;print(json.load(open('/tmp/login.json'))['access_token'])")
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": { "id": "nwzRAGt4uDW5sD8StstB5K", "username": "dosen.demo", "role": "INSTRUCTOR" }
}
```

Token berlaku 30 menit. `username` boleh berisi username **atau** email.
Password salah → `401 {"error":{"code":"AUTHENTICATION_FAILED","message":"Autentikasi gagal.","details":[]}}`.

Semua request di bawah butuh header `Authorization: Bearer $TOKEN`
(kecuali `/health` dan `/api/v1/auth/login`).

```bash
AUTH="Authorization: Bearer $TOKEN"
```

---

## 1. System ✅

```bash
curl -s "$BASE/health"                       # 200 {"status":"ok"}
curl -s "$BASE/openapi.json" | head -c 200   # 200 dokumen OpenAPI
```

---

## 2. Authentication ✅

```bash
curl -s "$BASE/api/v1/auth/me" -H "$AUTH"    # 200 profil user
```

---

## 3. Administration ✅ (role ADMIN)

```bash
curl -s "$BASE/api/v1/admin/users?search=dosen.demo" -H "$AUTH"
curl -s "$BASE/api/v1/admin/users/{user_id}" -H "$AUTH"
```

Role bukan ADMIN → `403 {"error":{"code":"AUTHORIZATION_DENIED",...}}`.

---

## 4. Instructor Setup ✅

```bash
curl -s "$BASE/api/v1/instructors/me/setup" -H "$AUTH"

curl -s -X PUT "$BASE/api/v1/instructors/me/setup" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{
  "instructor_profile": {
    "teaching_style": "Interaktif dengan studi kasus",
    "expertise": "Basis Data",
    "delivery_preference": "Banyak contoh query",
    "language_preference": "Bahasa Indonesia"
  },
  "activity_configuration": {
    "learning_material": true,
    "learning_resource": true,
    "assignment": true,
    "quiz": false
  },
  "additional_prompt": "Sertakan contoh SQL pada setiap materi."
}'
```

Semua aktivitas `false` → `422 INVALID_REQUEST` dengan detail per field.

---

## 5. RPS ✅

### 5.1 Unggah dokumen ✅

```bash
curl -s -X POST "$BASE/api/v1/rps" -H "$AUTH" \
  -F 'file=@backend/tests/fixtures/test.pdf;type=application/pdf'
# 201 {"rps_id":"...","status":"UPLOADED","schema_version":"2.0"}
```

### 5.2 Daftar & detail ✅

```bash
curl -s "$BASE/api/v1/rps" -H "$AUTH"
# 200 {"items":[{"id":"Vs2JzJavtAKyVeuU4GqkAB","filename":"contoh-rps-basis-data.pdf","status":"ANALYZED",...}]}

curl -s "$BASE/api/v1/rps/{rps_id}" -H "$AUTH"
```

### 5.3 Hasil analisis ✅

```bash
curl -s "$BASE/api/v1/rps/{rps_id}/analysis" -H "$AUTH"
# 200 {"rps_id":"...","analyzed_at":"...","data":{"schema_version":"2.0","course":{...},"weeks":[...]}}
```

### 5.4 Proses & analisis ulang ✅ (202, background)

```bash
curl -s -X POST "$BASE/api/v1/rps/{rps_id}/process" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{}'
# 202 {"rps_id":"...","status":"PROCESSING","workflow_id":"..."}

curl -s -X POST "$BASE/api/v1/rps/{rps_id}/reanalyze" -H "$AUTH"
# 202 {"rps_id":"...","status":"ANALYZING","workflow_id":"..."}
```

---

## 6. Workflow ✅ (BE-11)

```bash
curl -s "$BASE/api/v1/workflows" -H "$AUTH"
curl -s "$BASE/api/v1/workflows/{workflow_id}" -H "$AUTH"
curl -s "$BASE/api/v1/workflows/{workflow_id}/events" -H "$AUTH"
curl -s -X PUT "$BASE/api/v1/workflows/{workflow_id}/moodle-target" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"moodle_course_id": 12}'
# body {} ditolak 422; null mengosongkan target
```

Event real-time (WS, token lewat query karena browser tidak bisa set header di WS):

```bash
websocat "wss://columns-possess-tourist-costumes.trycloudflare.com/api/v1/ws/workflows/{workflow_id}?token=$TOKEN"
```

---

## 7. Courses ✅ baca / 🚧 tulis

Endpoint **baca** sudah live: `GET /courses`, `GET /courses/{id}`,
`GET /courses/{id}/plan`, `GET /courses/{id}/content` (`?week=N` opsional).
Endpoint **tulis** (generate, approve, regenerate, validation, review, execute)
belum ada dan masih `404 {"detail":"Not Found"}`; path & body-nya sudah dipakai
frontend (`frontend/src/services/courseService.js`) dan ditetapkan
`design-api.md` §8–§10.

Catatan: `course_id`, `plan_id`, dan `content_id` dibaca dari output
`scripts/seed_sample_course.py`.

### 7.1 Data contoh hasil seed

| Field | Nilai |
| --- | --- |
| `course_id` | dibaca dari output `seed_sample_course` |
| `shortname` | `IF2230-SAMPLE` |
| `course_plan_id` | output seed |
| `content_id` | id baris `contents` minggu terkait |

### 7.2 Daftar & detail course ✅

```bash
curl -s "$BASE/api/v1/courses" -H "$AUTH"
# 200 {"items":[{"id":"5AH7inFLxJDRKEa34saR9c","shortname":"IF2230-SAMPLE",
#      "fullname":"Basis Data (Contoh)","status":"DRAFT","semester":"3",
#      "moodle_course_id":null}]}

curl -s "$BASE/api/v1/courses/{course_id}" -H "$AUTH"
# 200 detail + instructor_id, rps_id, description, created_at, updated_at
# 404 RESOURCE_NOT_FOUND bila course bukan milik dosen yang login
```

`/courses/{course_id}/` (dengan garis miring) dialihkan `307` ke URL tanpa
garis miring.

### 7.3 Konfigurasi aktivitas per course 🚧

```bash
curl -s -X PUT "$BASE/api/v1/courses/{course_id}/activity-configuration" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{
  "learning_material": true,
  "learning_resource": true,
  "assignment": true,
  "quiz": false
}'
```

### 7.4 Course plan ✅ baca / 🚧 generate

```bash
curl -s "$BASE/api/v1/courses/{course_id}/plan" -H "$AUTH"
# 200 {"course_id":"...","plan_id":"gQCthdpqdDVgfqLFQ9TLSs","version":1,
#      "status":"PENDING_REVIEW","weeks":[{...16 minggu, 8=UTS, 16=UAS}]}
# versi plan tertinggi yang dipakai; course tanpa plan → plan_id null, weeks []

# belum ada (404):
curl -s -X POST "$BASE/api/v1/courses/{course_id}/plan" -H "$AUTH"
curl -s -X POST "$BASE/api/v1/courses/{course_id}/plan/approve" -H "$AUTH"
curl -s -X POST "$BASE/api/v1/courses/{course_id}/plan/regenerate" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"instruction":"Tambah studi kasus basis data kampus."}'
```

### 7.5 Konten mingguan ✅ baca / 🚧 generate

```bash
# baca hasil (live)
curl -s "$BASE/api/v1/courses/{course_id}/content" -H "$AUTH"
curl -s "$BASE/api/v1/courses/{course_id}/content?week=4" -H "$AUTH"
# 200 {"course_id":"...","weeks":[{"week":4,"topic":"Query SQL dan JOIN",
#      "learning_objectives":["SUB-3"],"materials":[{"content_id":"...","type":
#      "learning_material","version":1,"sections":[...],"body_markdown":"..."}],
#      "resources":[...],"activities":{"assignment":{...},"quiz":null}}]}
# hanya versi terbaru per (minggu, jenis) yang dikembalikan

# belum ada (404): generate & regenerasi
curl -s -X POST "$BASE/api/v1/courses/{course_id}/content/generate" -H "$AUTH" \
  -H 'Content-Type: application/json' -H "Idempotency-Key: $(uuidgen)" \
  -d '{"weeks":"all"}'

curl -s -X POST "$BASE/api/v1/courses/{course_id}/content/{content_id}/regenerate" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"instruction":"Perjelas contoh pada bagian kedua."}'
```

`instruction` wajib tidak kosong (`422 INVALID_REQUEST` dengan detail field).

### 7.6 Setelah konten ada (M03/M04) 🚧

```bash
curl -s -X POST "$BASE/api/v1/courses/{course_id}/validation" -H "$AUTH"
curl -s "$BASE/api/v1/courses/{course_id}/validation" -H "$AUTH"
curl -s "$BASE/api/v1/courses/{course_id}/review" -H "$AUTH"
curl -s -X POST "$BASE/api/v1/courses/{course_id}/review/approve" -H "$AUTH"
curl -s -X POST "$BASE/api/v1/courses/{course_id}/review/reject" -H "$AUTH" \
  -H 'Content-Type: application/json' -d '{"reason":"Materi minggu 4 tidak sesuai RPS."}'
curl -s -X POST "$BASE/api/v1/courses/{course_id}/execute" -H "$AUTH"
```

---

## 8. Bentuk error

Seluruh error memakai satu amplop (`design-api` §18):

```json
{ "error": { "code": "INVALID_REQUEST", "message": "Data RPS tidak valid.", "details": [] } }
```

`details` berisi `{"field": "...", "message": "..."}` untuk kesalahan validasi.
Kode yang mungkin muncul: `AUTHENTICATION_FAILED`, `AUTHORIZATION_DENIED`,
`RESOURCE_NOT_FOUND`, `INVALID_REQUEST`, `INVALID_FILE`, `RPS_PROCESSING_FAILED`,
`LLM_GENERATION_FAILED`, `VALIDATION_FAILED`, `REVIEW_REQUIRED`,
`EXECUTION_FAILED`, `MOODLE_ERROR`, `VERIFICATION_FAILED`, `WORKFLOW_FAILED`,
`INTERNAL_ERROR`.

Catatan: `404` karena **route tidak ada** keluar sebagai `{"detail":"Not Found"}`
(default FastAPI), bukan amplop di atas — penanda path belum diimplementasikan.
