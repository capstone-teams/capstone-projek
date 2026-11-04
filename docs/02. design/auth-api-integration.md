# Authentication API Integration Guide

**Issue:** BE-06.1 (parent BE-06) · **Status:** siap diintegrasikan frontend ·
**Kontrak sumber:** [`design-api.md`](design-api.md) §5, §18, §19, §22 ·
**Implementasi:** BE-03.3 (authentication) dan BE-03.4 (authorization)

Dokumen ini menjadi panduan integrasi frontend ke endpoint authentication
backend. Kontrak yang sama juga tersedia sebagai OpenAPI di environment
development, sehingga frontend tidak perlu membaca source code backend.

---

## 1. Alamat dokumentasi dan base URL

| Kebutuhan | Development |
| :--- | :--- |
| Base URL API | `http://localhost:8000/api/v1` |
| Swagger UI (coba request langsung) | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI mentah | `http://localhost:8000/openapi.json` |
| Health check | `http://localhost:8000/health` |

Jalankan backend dari folder `backend/`:

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI memakai base URL relatif terhadap halaman `/docs`, sehingga tombol
**Try it out** langsung mengarah ke server yang sama. Untuk endpoint `GET
/auth/me`, tekan **Authorize** dan isi token yang diperoleh dari login.

> Frontend Vite berjalan di `http://localhost:3000`. Origin tersebut sudah
> terdaftar pada konfigurasi CORS development; detail dan cara mengubahnya ada
> pada panduan BE-06.2 yang disertakan bersama konfigurasi CORS backend.

---

## 2. Ringkasan endpoint

| Method | Path | Authentication | Role | Keterangan |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/auth/login` | Tidak | Semua role | Verifikasi kredensial, terbitkan access token |
| `GET` | `/auth/me` | Bearer token | Semua role | Current user beserta role dari database |

Tidak ada endpoint logout pada API Specification. Logout dilakukan client
dengan menghapus token; lihat §5.

---

## 3. `POST /api/v1/auth/login`

### Request

```http
POST /api/v1/auth/login
Content-Type: application/json
```

```json
{
  "username": "dosen.demo@itk.ac.id",
  "password": "<password-akun-uji>"
}
```

| Field | Tipe | Wajib | Keterangan |
| :--- | :--- | :---: | :--- |
| `username` | string (1–255) | Ya | **Identifier login**: username Moodle **atau** email user |
| `password` | string (1–72) | Ya | Password akun; tidak pernah dikembalikan API |

Aturan identifier:

- email dicocokkan tanpa membedakan kapitalisasi;
- username dicocokkan persis lebih dulu, lalu tanpa membedakan kapitalisasi bila
  hasilnya tunggal;
- bila satu nilai cocok dengan email user A sekaligus username user B, **email
  diutamakan**;
- spasi di awal/akhir identifier diabaikan.

Akun uji instructor dan student disediakan oleh BE-06.3. Password-nya dibagikan
melalui kanal internal tim dan **tidak** di-commit ke repository.

### Response sukses — `200 OK`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIuLi4ifQ.signature",
  "token_type": "bearer",
  "user": {
    "id": "kY3vQ9mN2pLxR7tWzA5bcd",
    "role": "INSTRUCTOR"
  }
}
```

| Field | Keterangan |
| :--- | :--- |
| `access_token` | JWT bertanda tangan untuk header `Authorization` |
| `token_type` | Selalu `bearer` |
| `user.id` | Identifier user (ShortUUID 22 karakter) |
| `user.role` | Role kanonik: `INSTRUCTOR`, `STUDENT`, atau `ADMIN` |

> **Casing role:** response backend memakai nilai enum kanonik **huruf besar**
> (`INSTRUCTOR`, `STUDENT`, `ADMIN`). Contoh `"instructor"` pada design-api §5
> bersifat ilustratif; frontend harus memakai nilai dari response, bukan
> meng-hardcode contoh tersebut.

**Padanan istilah proposal.** Class diagram pada proposal memakai istilah
Indonesia. Nilai yang beredar di API, seed akun uji, dan OpenAPI tetap enum
kanonik — padanannya satu-satu, tidak ada nilai tambahan:

| Proposal | Nilai kanonik API | Akun uji (BE-06.3) |
| :--- | :--- | :--- |
| `DOSEN` | `INSTRUCTOR` | akun dosen pada `scripts/seed_test_accounts.py` |
| `MAHASISWA` | `STUDENT` | akun mahasiswa pada `scripts/seed_test_accounts.py` |
| — | `ADMIN` | operasi administrasi (`/api/v1/admin/*`) |

Endpoint khusus dosen menolak akun mahasiswa dengan `403 AUTHORIZATION_DENIED`
(design-api §22), dan role selalu dibaca ulang dari record User pada setiap
request (tidak menjadi klaim token).

Response tidak pernah memuat password, hash password, atau credential Moodle.

### Response gagal

| Status | `error.code` | Penyebab |
| :---: | :--- | :--- |
| `401` | `AUTHENTICATION_FAILED` | Identifier tidak terdaftar, password salah, user non-aktif, atau user tanpa credential lokal |
| `422` | `VALIDATION_FAILED` | Body tidak memenuhi schema (field wajib kosong, password terlalu panjang, dsb.) |

```json
{
  "error": {
    "code": "AUTHENTICATION_FAILED",
    "message": "Autentikasi gagal.",
    "details": []
  }
}
```

Semua penyebab 401 memakai pesan yang **identik** agar response tidak dapat
dipakai menebak user yang terdaftar (*user enumeration*). Response 401
menyertakan header `WWW-Authenticate: Bearer`.

---

## 4. `GET /api/v1/auth/me`

### Request

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

### Response sukses — `200 OK`

```json
{
  "id": "kY3vQ9mN2pLxR7tWzA5bcd",
  "username": "dosen.demo",
  "firstname": "Dosen",
  "lastname": "Demo",
  "email": "dosen.demo@itk.ac.id",
  "role": "INSTRUCTOR"
}
```

Role dan status dibaca ulang dari record User pada setiap request. Perubahan
role atau deaktivasi user berlaku pada request berikutnya tanpa perlu token
baru.

### Response gagal

| Status | `error.code` | Penyebab |
| :---: | :--- | :--- |
| `401` | `AUTHENTICATION_FAILED` | Header tidak ada, skema bukan `Bearer`, token tidak valid/kedaluwarsa, atau user non-aktif |

---

## 5. Format, masa berlaku, dan kedaluwarsa token

Token adalah **JWT compact** bertanda tangan `HS256` dengan klaim:

| Klaim | Isi | Keterangan |
| :--- | :--- | :--- |
| `sub` | ShortUUID user (22 karakter) | Identifier user; divalidasi ulang saat decode |
| `iat` | Unix timestamp | Waktu token diterbitkan |
| `exp` | Unix timestamp | Waktu token kedaluwarsa |
| Role | — | **Tidak** ada di token; role selalu dibaca dari database |

- **Masa berlaku** mengikuti `ACCESS_TOKEN_EXPIRE_MINUTES` (default **30
  menit**). Nilai production ditentukan deployment configuration.
- **Kedaluwarsa:** endpoint terproteksi menjawab `401 AUTHENTICATION_FAILED`
  dengan header `WWW-Authenticate: Bearer`. Frontend harus menghapus token,
  menampilkan pemberitahuan sesi berakhir, lalu mengarahkan user ke login.
- **Tidak ada refresh token maupun endpoint logout.** Logout = hapus token di
  client. Karena token stateless, token yang sudah dicuri tetap valid sampai
  `exp`; masa berlaku pendek dan `SECRET_KEY` yang kuat adalah pengendalinya.
- Frontend tidak boleh menyimpan password atau menaruh token pada URL/log.
  Kirim token hanya melalui header `Authorization`.

Contoh memeriksa `exp` dari token (opsional, untuk debugging):

```bash
python - <<'PY'
import base64, json, os
token = os.environ["TOKEN"]
payload = token.split(".")[1]
payload += "=" * (-len(payload) % 4)
print(json.loads(base64.urlsafe_b64decode(payload)))
PY
```

---

## 6. Role dan authorization

Role yang dikenal backend:

| Role | Penggunaan |
| :--- | :--- |
| `INSTRUCTOR` | Dosen: seluruh operasi RPS, perencanaan, konten, review, eksekusi Moodle |
| `STUDENT` | Mahasiswa: hanya melihat hasil course |
| `ADMIN` | Operasi administrasi user (`/api/v1/admin/users`) |

Matriks akses dari design-api §22:

| Operation | Instructor | Student |
| :--- | :---: | :---: |
| Upload RPS | Yes | No |
| Process RPS | Yes | No |
| View RPS Analysis | Yes | No |
| Manage Instructor Profile | Yes | No |
| Generate Course Plan | Yes | No |
| Review Course Plan | Yes | No |
| Generate Content | Yes | No |
| Review Content | Yes | No |
| Approve Content | Yes | No |
| Execute to Moodle | Yes | No |
| Monitor Agent | Yes | No |
| View Verification | Yes | No |
| Access Result Course | Yes | Yes |

Endpoint administrasi `GET /api/v1/admin/users` dan
`GET /api/v1/admin/users/{user_id}` hanya boleh diakses `ADMIN` (BE-03.4).

Perbedaan status kegagalan:

| Status | `error.code` | Arti |
| :---: | :--- | :--- |
| `401` | `AUTHENTICATION_FAILED` | Identitas belum terbukti: login gagal atau token tidak valid |
| `403` | `AUTHORIZATION_DENIED` | Identitas valid, tetapi role tidak diizinkan menjalankan operasi |

Guard authorization berjalan **sebelum** handler endpoint. Role tidak pernah
diambil dari body, query, header buatan client, maupun klaim token.

---

## 7. Format error dan kode autentikasi

Seluruh error endpoint (error domain maupun validasi request) mengikuti
design-api §18:

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Data request tidak valid.",
    "details": [
      { "field": "password", "message": "Field required" }
    ]
  }
}
```

| Status | `error.code` | Konteks |
| :---: | :--- | :--- |
| `400` | `INVALID_REQUEST` / `INVALID_FILE` | Request/berkas tidak sah pada endpoint tertentu |
| `401` | `AUTHENTICATION_FAILED` | Login gagal atau token tidak ada/tidak valid/kedaluwarsa |
| `403` | `AUTHORIZATION_DENIED` | Role tidak diizinkan |
| `404` | `RESOURCE_NOT_FOUND` | Resource tidak ditemukan atau bukan milik user |
| `409` | `INVALID_REQUEST` | Konflik state operasi |
| `422` | `VALIDATION_FAILED` | Body/path tidak memenuhi schema |
| `500` | `INTERNAL_ERROR` | Kegagalan tak terduga; detail teknis hanya di log server |

Catatan:

- `details` selalu ada (array; boleh kosong).
- Nilai input **tidak** pernah di-echo pada error validasi; body login berisi
  password.
- Pesan error tidak membocorkan detail implementasi, credential, atau token.
- Daftar kode lengkap untuk seluruh modul ada di design-api §18.

---

## 8. Alur integrasi frontend

```text
User mengisi identifier + password
              │
              ▼
POST /api/v1/auth/login
              │
      ┌───────┴────────┐
      │ 200            │ 401 / 422
      ▼                ▼
Simpan access_token   Tampilkan pesan error
      │
      ▼
GET /api/v1/auth/me  ── 200 ──▶ simpan user + role
      │
      └── 401 ──▶ hapus token, kembali ke login
```

Langkah minimum:

1. Kirim `POST {BASE}/auth/login` dengan `{ username, password }`.
2. Simpan `access_token` (mengikuti strategi penyimpanan frontend) dan buang
   saat logout.
3. Untuk request terproteksi, kirim `Authorization: Bearer <access_token>`.
4. Pada setiap `401`, hapus token dan arahkan user ke login; jangan retry
   otomatis tanpa token baru.
5. Gunakan `error.code` untuk percabangan, bukan teks `message`.
6. Status `403` berarti user sudah login tetapi role-nya tidak diizinkan; jangan
   memperlakukannya sebagai sesi berakhir.

### Konfigurasi environment frontend

Vite mem-proxy `/api` ke backend sehingga default development tidak memerlukan
CORS:

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_BACKEND_URL=http://localhost:8000
```

Bila frontend memanggil backend langsung (tanpa proxy), gunakan
`VITE_API_BASE_URL=http://localhost:8000/api/v1` dan pastikan origin frontend
terdaftar pada `CORS_ORIGINS` backend. Detail: panduan BE-06.2.

---

## 9. Verifikasi manual dengan curl

```bash
BASE=http://localhost:8000/api/v1

# 1. Login (isi password dari kanal internal; hindari menyimpannya di shell history)
read -r -s -p "Password: " PASSWORD; echo
LOGIN=$(curl -sS -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"dosen.demo@itk.ac.id\",\"password\":\"$PASSWORD\"}")

TOKEN=$(python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])' <<<"$LOGIN")

# 2. Current user
curl -sS "$BASE/auth/me" -H "Authorization: Bearer $TOKEN"

# 3. Token tidak valid harus 401
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/auth/me" \
  -H "Authorization: Bearer token-tidak-valid"
```

Contoh response `GET /auth/me` terdapat pada §4.

---

## 10. Traceability dan definisi selesai

| Requirement BE-06.1 | Bukti |
| :--- | :--- |
| Dokumentasi login dan current user beserta contoh request/response/error | Swagger UI `/docs`, `src/routes/auth.py`, `src/schemas/auth.py`, dokumen ini |
| Penjelasan format token, masa berlaku, dan perilaku kedaluwarsa | §5 dokumen ini; deskripsi `access_token` pada OpenAPI |
| Daftar role dan akses berdasarkan Authorization Matrix | §6 dokumen ini; schema `UserRole` pada OpenAPI |
| Format error §18 dan daftar kode autentikasi | §7 dokumen ini; schema `ErrorResponse`; handler `RequestValidationError` |
| Dokumentasi dapat diakses pada environment development | `/docs`, `/redoc`, `/openapi.json`; diuji `tests/test_auth_documentation.py` |
| Direview oleh FE A | Pull Request BE-06.1 (reviewer frontend) |

Acceptance criteria terpenuhi apabila Swagger UI menampilkan kedua endpoint
dengan contoh yang dapat dijalankan, dan frontend dapat mengikuti dokumen ini
tanpa membaca source code backend.
