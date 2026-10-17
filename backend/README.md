# Backend Module

Folder ini berisi *source code*, konfigurasi, dan pengujian untuk service backend yang dibangun menggunakan **FastAPI**, **SQLAlchemy**, dan **Pydantic**.

---

## 🏗️ Structure Overview

```text
backend/
├── migrations/                   # Skrip & histori migrasi database (Alembic)
│   ├── versions/                 # File revisi migrasi skema DB (.py)
│   └── env.py                    # Konfigurasi runtime environment Alembic
├── alembic.ini                   # File konfigurasi utama Alembic
├── src/                          # Source code utama aplikasi
│   ├── config/                   # Konfigurasi aplikasi, env vars, & infrastruktur DB
│   │   ├── settings.py           # Pydantic Settings (environment variables)
│   │   └── database.py           # Async engine & session factory
│   ├── routes/                   # Definition Endpoint API & HTTP Router (FastAPI)
│   │   ├── admin.py              # GET /admin/users (ADMIN only)
│   │   ├── auth.py               # POST /auth/login, GET /auth/me
│   │   ├── rps.py                # POST /rps, GET /rps/{id}, POST /rps/{id}/process
│   │   ├── health.py
│   │   └── __init__.py           # Registri router terpusat (api_router)
│   ├── controllers/              # HTTP Request Orchestrator / Data Mapping Layer
│   ├── services/                 # Core Business Logic, Data Access, & External APIs
│   │   ├── auth/                 # Authentication & authorization: kredensial, token, AuthService, RolePolicy
│   │   ├── rps/                  # Unggah, penyimpanan, & konversi dokumen RPS (BE-05)
│   │   ├── user/                 # Domain User/Role, UserService, UserRepository
│   │   ├── llm/                  # Integrasi penyedia LLM
│   │   └── dependencies.py       # Dependency provider untuk routes (+ require_roles)
│   ├── models/                   # Database Entities / ORM Models (SQLAlchemy)
│   ├── schemas/                  # Request & Response DTOs / Data Validation (Pydantic)
│   │   ├── admin.py              # DTO operasi administrasi
│   │   ├── auth.py
│   │   ├── rps.py                # DTO endpoint RPS
│   │   └── rps_structured.py     # Kontrak RPS Structured Data (BE-05.3)
│   ├── middlewares/              # FastAPI Middlewares (Error Handler, Auth, CORS)
│   │   └── error_handlers.py     # Pemetaan error domain → response HTTP
│   ├── utils/                    # Helper functions & pure utilities
│   └── main.py                   # FastAPI Application Entry Point
├── tests/                        # Automated unit & integration tests (pytest)
│   ├── conftest.py               # Fixture bersama (session SQLite in-memory)
│   ├── test_admin_routes.py      # Endpoint administrasi (ADMIN only)
│   ├── test_authorization.py     # Mekanisme role authorization
│   ├── test_auth_postgres.py     # Integrasi authentication vs PostgreSQL sungguhan
│   └── test_*.py                 # Unit & route test per modul
├── pyproject.toml                # Konfigurasi dependensi & tools (uv)
├── pytest.ini                    # Konfigurasi test runner pytest
├── uv.lock                       # Lockfile dependensi uv
└── README.md                     # Dokumentasi arsitektur backend
```

---

## 🔀 Aliran Dependency Antar-Layer (Dependency Flow)

Setiap request melewati layer secara berurutan. Panah di bawah menunjukkan arah pemanggilan yang **diizinkan**:

```text
                        HTTP Request
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/routes/                 │
              │  API Layer                   │
              │  (HTTP contract saja)        │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/controllers/            │  ← opsional
              │  Orchestrator / Data Mapping │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/services/               │
              │  Business Logic / Domain     │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  Repository / Data Access    │  ← opsional
              │  (berada di dalam services/) │
              └──────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  src/models/ + PostgreSQL    │
              │  Persistence (SQLAlchemy)    │
              └──────────────────────────────┘
```

Poin penting:

1. Dependency hanya boleh mengalir **satu arah (turun)**. Layer bawah **dilarang** mengimpor layer di atasnya (contoh: `services/` tidak boleh mengimpor `routes/`).
2. `src/routes/` **tidak boleh** melewati `src/services/` untuk menyentuh database secara langsung.
3. `src/controllers/` dan **Repository / Data Access** bersifat **opsional**. Keduanya dibuat hanya jika sebuah fitur benar-benar membutuhkannya, tetapi batas tanggung jawab setiap layer tetap harus jelas.
4. Request **tidak boleh melompati layer**: `routes/` memanggil `services/`, bukan ORM/SQLAlchemy secara langsung.

---

## 🔒 Aturan Import Antar-Layer

| Layer | BOLEH Mengimpor | DILARANG Mengimpor |
| :--- | :--- | :--- |
| **`src/routes/`** | `controllers/`, `services/`, `schemas/`, `utils/`, primitif FastAPI (`APIRouter`, `Depends`, `HTTPException`) | `models/`, `sqlalchemy`, `Session` / `AsyncSession` |
| **`src/controllers/`** | `services/`, `schemas/`, `utils/` | `models/`, `sqlalchemy`, `Session` / `AsyncSession` |
| **`src/services/`** | `models/`, `schemas/`, `config/`, `utils/`, service lain di dalam `services/` | `routes/`, `controllers/`, objek `Request` / `Response` FastAPI |
| **`src/models/`** | `config/` (Base & tipe kolom), `sqlalchemy` | `schemas/`, `services/`, `routes/` |
| **`src/schemas/`** | `pydantic` | `sqlalchemy`, `models/`, `services/` |
| **`src/config/`** | library eksternal & environment variables | `routes/`, `controllers/`, `services/`, `models/` |
| **`src/utils/`** | library standar / library murni | seluruh layer aplikasi (`routes/`, `controllers/`, `services/`, `models/`) |
| **`src/middlewares/`** | `config/`, `utils/`, primitif FastAPI (`Request`, `Response`) | logika domain yang berada di `services/` |

Catatan tambahan:

- `src/services/` adalah **satu-satunya** layer yang boleh memegang `Session` database.
- `src/services/` tidak boleh membangun respons HTTP atau melempar `HTTPException` mentah. Error domain dilempar sebagai exception domain, lalu dipetakan ke HTTP status oleh `routes/` atau `middlewares/`.

---

## 🎯 Tanggung Jawab Setiap Layer (Separation of Concerns)

Untuk menjaga konsistensi dan mencegah duplikasi fungsi antar layer, seluruh anggota tim backend **wajib** mematuhi pembagian peran berikut:

| Layer / Direktori | Responsibilitas Utama | Yang BOLEH Dilocate | Yang TIDAK BOLEH Dilocate |
| :--- | :--- | :--- | :--- |
| **`src/main.py`** | Application Entry Point | Inisialisasi FastAPI app, registrasi router & middleware global, event lifespan (startup/shutdown). | Logika bisnis, query database, definisi route individual. |
| **`src/config/`** | System Configuration & Core Setup | Pydantic `BaseSettings` (`settings.py`), inisialisasi Database Engine/Session, environment constants. | Logika bisnis, HTTP error response formatting. |
| **`src/routes/`** | API Router & HTTP Request Handling | Definisi endpoint HTTP (GET, POST, PUT, DELETE), validasi input URL/Header (`Depends`), memanggil Controller/Service, mengembalikan response HTTP. | Direct SQL / ORM Queries, transaksi database, logika integrasi pihak ketiga. |
| **`src/controllers/`** | Request Orchestrator *(Opsional)* | Menghubungkan request dari route ke satu atau beberapa service, formatting data response DTO. | Menulis query DB langsung, logika bisnis inti yang kompleks. |
| **`src/services/`** | Business Logic & External Integrations | Seluruh logika bisnis aplikasi, query/mutasi DB via SQLAlchemy Session, integrasi sistem & API pihak ketiga. | Direct HTTP Request/Response handling, Pydantic HTTP error raising secara mentah. |
| **`src/models/`** | Database Entities (SQLAlchemy) | Pemetaan tabel database, kolom, tipe data DB, dan relasi antar tabel (Foreign Keys, Relationships). | Validasi HTTP Request Body, Pydantic models. |
| **`src/schemas/`** | Data Transfer Objects (Pydantic) | Validasi struktur data Request Body, Query Params, dan Response Body (DTO), serialization & deserialization JSON. | Relasi ORM database, query database. |
| **`src/middlewares/`** | Cross-cutting HTTP Concerns | Interceptor request/response, global exception handler, CORS headers, authentication JWT middleware. | Logika spesifik domain bisnis. |
| **`src/utils/`** | Shared Utilities | Pure helper functions yang reusable dan tanpa side-effect (misal: date formatter, string parser, crypto helpers). | State aplikasi, logika domain backend. |
| **`alembic/`** | Database Schema Migrations | Skrip versi pergerakan skema DB (`alembic/versions/`), konfigurasi migrasi (`env.py`). | Data dummy, aplikasi runtime code. |

---

## ⚠️ Aturan Pencegahan Duplikasi Layer

1. **`models/` vs `schemas/`**:
   - `models/` **hanya** berisi kelas SQLAlchemy yang merepresentasikan struktur tabel database.
   - `schemas/` **hanya** berisi kelas Pydantic untuk validasi input HTTP request dan formatting output JSON response.
   - **Dilarang** mencampurkan Pydantic schema di dalam `models/` atau kelas SQLAlchemy di dalam `schemas/`.

2. **`routes/` vs `services/`**:
   - Route handler **tidak boleh** mengeksekusi query database (`select`, `insert`, `update`) secara langsung.
   - Semua operasi data dan logika domain harus didelegasikan ke `services/`.

3. **`services/` vs `utils/`**:
   - `services/` menampung logika yang *stateful* atau memiliki context domain (DB, external APIs).
   - `utils/` menampung fungsi murni (*stateless*) yang tidak terikat pada domain bisnis tertentu.

---

## 🗄️ Repository / Data Access (Opsional)

Struktur direktori backend **bersifat tetap** (lihat Structure Overview), sehingga tidak ada direktori `repositories/` terpisah. Data access berada di dalam `src/services/`.

Kapan sebuah fitur perlu memisahkan data access menjadi repository?

- Service mulai memuat query yang panjang, berulang, atau menggabungkan lebih dari satu entity.
- Query yang sama dipakai oleh lebih dari satu service.

Pola penamaan: `src/services/<domain>_repository.py` (contoh: `src/services/rps_repository.py`, `src/services/content_repository.py`).

Untuk domain yang memuat lebih dari satu modul internal, gunakan bentuk paket `src/services/<domain>/` dengan pemisahan `repository.py` (data access) dan `service.py` (operasi aplikasi) — seperti pada `src/services/llm/` dan `src/services/user/`.

Aturan Repository:

1. Repository **hanya** berisi operasi data (query & mutasi) — tanpa aturan bisnis, kalkulasi domain, atau percabangan workflow.
2. Repository hanya boleh dipanggil oleh `services/`. `routes/` dan `controllers/` **dilarang** memanggil repository secara langsung.
3. Jika sebuah fitur belum membutuhkan query kompleks, repository **tidak perlu dibuat**. Service boleh langsung memakai `Session` — yang penting tanggung jawab tersebut tetap berada di layer service, bukan di router.

---

## 🔐 Authentication (BE-03.3)

Authentication menjawab **"siapa User ini?"**. Keputusan boleh/tidaknya sebuah operasi dijalankan berada di authorization (BE-03.4), bukan di sini.

### Endpoint

| Method | Path | Keterangan |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | Verifikasi kredensial; mengembalikan `access_token`, `token_type`, dan identitas (`id`, `role`) |
| `GET` | `/api/v1/auth/me` | Mengembalikan current user (`id`, `username`, `firstname`, `lastname`, `email`, `role`); membutuhkan header `Authorization: Bearer <access_token>` |

Field `username` pada body login adalah **identifier login** dan boleh berisi **username** maupun **email** user. Email dicocokkan tanpa membedakan kapitalisasi; username dicocokkan persis terlebih dahulu, lalu tanpa membedakan kapitalisasi bila hasilnya tunggal. Kolom `users.username` adalah atribut user Moodle — dipakai saat user dibuat/di-sinkronkan ke Moodle (BE-04) — dan sekarang juga dapat dipakai untuk login lokal. Bila sebuah nilai cocok dengan email user A sekaligus username user B, email diutamakan.

Field identity user (`username`, `firstname`, `lastname`, `email`, `password`) sengaja memakai nama atribut Moodle (`core_user_create_users`) supaya sinkronisasi tidak memerlukan tabel pemetaan tersendiri. `password` menyimpan **hash** bcrypt (lihat `src/services/auth/passwords.py`); password mentah tidak pernah disimpan.

Identifier user memakai **ShortUUID** (`src/models/base.py`: `ID_LENGTH = 22`), bukan UUID: kolom `users.id` bertipe `String(22)` dan path parameter seperti `/api/v1/admin/users/{user_id}` divalidasi terhadap bentuk tersebut (422 bila salah bentuk), dengan aturan yang sama berlaku di domain (`src/services/user/validation.py`).

### Memakai authentication pada endpoint baru

```python
# src/routes/rps.py
from fastapi import APIRouter, Depends

from src.services.dependencies import get_current_user
from src.services.user.domain import User

router = APIRouter(prefix="/rps", tags=["RPS"])

@router.post("")
async def create_rps(current_user: User = Depends(get_current_user)):
    ...  # current_user.role selalu berasal dari record User
```

### Di mana komponennya berada

| Komponen | Lokasi |
| :--- | :--- |
| Verifikasi kredensial, penerbitan/validasi token, current user | `src/services/auth/` |
| DTO request/response | `src/schemas/auth.py` |
| Endpoint HTTP | `src/routes/auth.py` |
| Pemetaan error domain → 401 `AUTHENTICATION_FAILED` | `src/middlewares/error_handlers.py` |
| Dependency provider (session, service, current user) | `src/services/dependencies.py` |
| Infrastruktur engine & session | `src/config/database.py` |

### Ketetapan yang berlaku untuk modul ini

1. **Dependency provider berada di dalam layer `services/`** (`src/services/dependencies.py`). Aturan layer sebelumnya menyisakan penempatan ini terbuka sampai database session didefinisikan; dengan penempatan ini router tetap **tidak** mengimpor SQLAlchemy dan cukup memakai `Depends(...)`.
2. **`src/schemas/` boleh mengimpor enum role** dari `src.services.user.enums` (sumber tunggal nilai role/status). Alternatifnya adalah mendefinisikan ulang nilai role di DTO, yang justru melanggar aturan BE-03.1. Selain enum tersebut, schema tetap hanya berisi Pydantic dan bebas SQLAlchemy.
3. **Role tidak pernah berasal dari client.** Role pada authentication state dibaca ulang dari record User setiap request (`AuthService.get_authenticated_user`), sehingga perubahan role atau deaktivasi langsung berlaku dan privilege tidak dapat dinaikkan lewat payload maupun klaim token.
4. **Semua kegagalan authentication menghasilkan response identik** (401 `AUTHENTICATION_FAILED`) untuk email tidak terdaftar, password salah, user non-aktif, user tanpa credential lokal, dan token tidak valid — mencegah *user enumeration*. Detail penyebab hanya dicatat server-side, tanpa nilai credential/token.
5. **`SECRET_KEY` produksi wajib berasal dari environment configuration yang aman.** Saat startup aplikasi mencatat peringatan (tanpa mencetak nilainya) bila `SECRET_KEY` lebih pendek dari 32 karakter; nilai contoh pada `.env.example` tidak layak dipakai di produksi.
6. **Pengujian integrasi membutuhkan PostgreSQL sungguhan** dan otomatis dilewati bila database tidak tersedia — lihat `tests/test_auth_postgres.py`.

---

## 🛡️ Authorization (BE-03.4)

Authorization menjawab **"bolehkah User ini menjalankan operation ini?"** dan hanya berjalan untuk user yang **sudah** terautentikasi (BE-03.3). Keduanya dipisah: kegagalan authentication menghasilkan 401 `AUTHENTICATION_FAILED`, sedangkan kegagalan authorization menghasilkan 403 `AUTHORIZATION_DENIED`.

Alur:

```text
Authenticated Request → Current User (dari record User) → User Role
        → Authorization Guard (RolePolicy) → Allowed / Denied (403)
```

### Memakai role authorization pada endpoint

```python
# src/routes/rps.py
from fastapi import APIRouter, Depends

from src.services.dependencies import require_roles
from src.services.user.domain import User
from src.services.user.enums import UserRole

router = APIRouter(prefix="/rps", tags=["RPS"])

# Single-role restriction: cukup sebagai dependency, handler tidak perlu tahu.
@router.post("", dependencies=[Depends(require_roles(UserRole.INSTRUCTOR))])
async def create_rps(...): ...

# Multiple-role restriction, dengan identitas yang sudah diotorisasi dipakai handler:
@router.get("/{rps_id}")
async def read_rps(
    rps_id: str,
    current_user: User = Depends(require_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)),
): ...  # current_user.role sudah dipastikan termasuk role yang diizinkan
```

Contoh nyata yang berlaku sekarang: `src/routes/admin.py` — seluruh endpoint `/api/v1/admin/users` memakai satu policy `admin_only = require_roles(UserRole.ADMIN)`.

### Endpoint

| Method | Path | Role yang diizinkan | Keterangan |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/admin/users` | `ADMIN` | Daftar seluruh user (diurutkan berdasarkan email) |
| `GET` | `/api/v1/admin/users/{user_id}` | `ADMIN` | Detail satu user; 404 `RESOURCE_NOT_FOUND` bila tidak ada |

Respons kegagalan mengikuti design-api §18/§19:

| Kondisi | Status | `error.code` |
| :--- | :--- | :--- |
| Tanpa token, token tidak valid/kedaluwarsa, atau user non-aktif | 401 | `AUTHENTICATION_FAILED` (+ header `WWW-Authenticate: Bearer`) |
| Role user tidak termasuk role yang dibutuhkan | 403 | `AUTHORIZATION_DENIED` (tanpa challenge header) |

### Di mana komponennya berada

| Komponen | Lokasi |
| :--- | :--- |
| Keputusan allow/deny berbasis role (`RolePolicy`) | `src/services/auth/authorization.py` |
| Dependency factory `require_roles(...)` | `src/services/dependencies.py` |
| Error domain authorization (403 `AUTHORIZATION_DENIED`) | `src/services/auth/errors.py` |
| Pemetaan error domain → response HTTP | `src/middlewares/error_handlers.py` |
| Contoh pemakaian pada endpoint | `src/routes/admin.py` |
| DTO operasi administrasi | `src/schemas/admin.py` |

### Ketetapan yang berlaku untuk modul ini

1. **Keputusan authorization berada di layer `services/`, bukan di router.** `RolePolicy` adalah value object murni (tanpa FastAPI, tanpa database) di `src/services/auth/authorization.py`; dependency factory `require_roles(...)` berada di `src/services/dependencies.py` — tempat seluruh provider dependency HTTP sudah berada (BE-03.3). Router hanya memasang `Depends(require_roles(...))`, sehingga pengecekan role tidak ditulis ulang maupun tersebar di setiap handler.
2. **Authorization dijalankan sebelum business operation.** Karena berupa dependency FastAPI, ia selesai sebelum handler endpoint dieksekusi; `tests/test_authorization.py` membuktikannya dengan endpoint yang mencatat eksekusinya.
3. **Authentication diperiksa lebih dulu.** `require_roles(...)` me-resolve `get_current_user` terlebih dahulu, sehingga request tanpa authentication (atau user non-aktif) selalu berhenti di 401 dan hanya user terautentikasi yang role-nya dievaluasi. Guard tidak dapat dilewati dengan menghilangkan identity.
4. **Role selalu berasal dari record User.** `RolePolicy` hanya melihat `user.role` milik current user; tidak ada parameter role yang berasal dari request. Role pada body, query, header (`X-Role`, dsb.), maupun klaim JWT buatan client tidak pernah dipercaya — semuanya diuji di `tests/test_authorization.py`. Perubahan role berlaku pada request berikutnya tanpa token baru, karena role dibaca ulang dari database.
5. **Single-role dan multiple-role restriction memakai satu mekanisme.** `require_roles(UserRole.ADMIN)` membatasi ke satu role secara eksplisit (ADMIN pun tidak otomatis boleh pada operation INSTRUCTOR-only), sedangkan `require_roles(UserRole.INSTRUCTOR, UserRole.STUDENT)` mengizinkan salah satu.
6. **Policy salah tulis gagal cepat.** Policy tanpa role atau dengan role yang tidak dikenal (misalnya `"SUPERADMIN"`) memunculkan `AuthorizationPolicyError` saat factory dipanggil (wiring endpoint), bukan 403 yang menyesatkan saat runtime.
7. **Kegagalan authorization konsisten dan tidak membocorkan detail.** Selalu 403 `AUTHORIZATION_DENIED` dengan pesan publik yang sama, tanpa menyebut role yang dibutuhkan maupun role user tersebut; detailnya hanya dicatat server-side. 403 juga tidak memakai header `WWW-Authenticate` karena bukan kegagalan authentication.
8. **Mekanisme siap diperluas.** `RolePolicy` adalah titik perluasan untuk resource/policy authorization pada tahap berikutnya (cukup menambah aturan di `RolePolicy.enforce` atau menyediakan policy baru dengan bentuk yang sama) tanpa mengubah cara endpoint memakainya.
9. **Satu policy dapat dipakai oleh banyak endpoint.** Router `admin` mendefinisikan `admin_only` sekali dan memakainya di dua endpoint; endpoint fitur lain (mis. RPS instructor-only) cukup memakai `require_roles(...)` yang sama ketika fiturnya diimplementasikan.

---

## 📘 Dokumentasi API Authentication (BE-06.1)

Frontend dapat memakai endpoint authentication tanpa membaca source code
backend. Dokumentasi tersedia otomatis dari OpenAPI saat server development
berjalan:

| URL | Isi |
| :--- | :--- |
| `http://localhost:8000/docs` | Swagger UI dengan contoh request/response dan tombol **Try it out** |
| `http://localhost:8000/redoc` | ReDoc |
| `http://localhost:8000/openapi.json` | Dokumen OpenAPI mentah |

Panduan integrasi lengkap — contoh login dan current user, format/masa berlaku
token, perilaku token kedaluwarsa, matriks role, format error §18, serta
walkthrough `curl` — berada di
[`docs/02. design/auth-api-integration.md`](../docs/02.%20design/auth-api-integration.md).

Ringkasan kontrak:

| Endpoint | Sukses | Gagal |
| :--- | :--- | :--- |
| `POST /api/v1/auth/login` | `200` + `access_token`, `token_type`, `user.id`, `user.role` | `401 AUTHENTICATION_FAILED`, `422 VALIDATION_FAILED` |
| `GET /api/v1/auth/me` | `200` + identity user dan role | `401 AUTHENTICATION_FAILED` (+ `WWW-Authenticate: Bearer`) |

Token adalah JWT `HS256` dengan klaim `sub`/`iat`/`exp`; role **tidak** menjadi
klaim token dan selalu dibaca ulang dari database. Masa berlaku mengikuti
`ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 menit). Tidak ada endpoint
refresh/logout — logout dilakukan client dengan menghapus token.

Semua error memakai amplop design-api §18. Sejak BE-06.1, error validasi request
juga memakai amplop tersebut (`422 VALIDATION_FAILED`) alih-alih bentuk default
FastAPI, dan nilai input (termasuk password) tidak pernah di-echo.

Dokumentasi ini diuji otomatis oleh `tests/test_auth_documentation.py`, termasuk
ketersediaan `/docs`, `/redoc`, `/openapi.json`, kelengkapan contoh, security
scheme Bearer, dan format error.

---

## 📄 RPS Upload & Docling Conversion (BE-05)

Modul ini menyediakan alur awal pemrosesan RPS: mengunggah dan menyimpan dokumen
RPS, mengonversinya menjadi Markdown/JSON/YAML beserta struktur tabel, dan
menetapkan **RPS Structured Data Schema** yang menjadi kontrak data untuk tahap
ekstraksi pada BE-08.

```text
RPS PDF ──▶ unggah (file_hash) ──▶ simpan berkas asli
                                        │
                                        ▼
                     POST /rps/{id}/process  ──▶ 202 PROCESSING (dijadwalkan)
                                        │                      │
                                        │              GET /rps/{id}  ← polling
                                        ▼
                        Docling ────────┴──▶ source_markdown  (kolom rps)
                                             source_document  (JSONB: JSON Docling)
                                             ├─ document.json  ┐
                                             ├─ document.yaml  ├─ artefak di
                                             ├─ tables.json    │  samping berkas
                                             └─ conversion.json┘
```

### Endpoint

| Method | Path | Role | Keterangan |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/rps` | `INSTRUCTOR` | Unggah RPS (`multipart/form-data`, field `file`). `201` untuk dokumen baru, `200` + `deduplicated: true` bila isi yang sama sudah pernah diunggah |
| `GET` | `/api/v1/rps/{rps_id}` | `INSTRUCTOR` | Detail dokumen beserta `source_markdown`-nya |
| `POST` | `/api/v1/rps/{rps_id}/process` | `INSTRUCTOR` | **Menjadwalkan** konversi: `202` + `PROCESSING`, atau `200` + `reused: true` bila sudah pernah diproses. Body opsional `{"schema_version": "..."}` |

Authorization mengikuti design-api §22 (Student: `No` untuk seluruh operasi RPS).
Seluruh endpoint memakai satu policy `instructor_only`.

Respons kegagalan mengikuti design-api §18/§19:

| Kondisi | Status | `error.code` |
| :--- | :--- | :--- |
| Ekstensi/ukuran/isi berkas tidak sah | 400 | `INVALID_FILE` |
| Nilai domain tidak valid (mis. hash cacat) | 422 | `INVALID_REQUEST` |
| RPS tidak ada atau milik instructor lain | 404 | `RESOURCE_NOT_FOUND` |
| Status RPS tidak mengizinkan operasi (mis. sedang diproses request lain) | 409 | `INVALID_REQUEST` |
| Konversi gagal (dokumen rusak, hasil kosong, model tidak tersedia) | 500 | `RPS_PROCESSING_FAILED` |
| Penyimpanan berkas gagal | 500 | `INTERNAL_ERROR` |

### Pemrosesan berjalan di background

`POST /rps/{id}/process` tidak menahan request: endpoint menandai dokumen
`PROCESSING`, menjadwalkan konversi, lalu menjawab `202` (design-api §6.3).
Konversinya dijalankan oleh `src/services/rps/runner.py` **setelah** response
dikirim, memakai session database sendiri — session milik request sudah tertutup
saat itu.

```bash
# 1. jadwalkan
curl -X POST /api/v1/rps/{id}/process -H "Authorization: Bearer $TOKEN"
# → 202 {"status": "PROCESSING", "reused": false}

# 2. pantau
curl /api/v1/rps/{id} -H "Authorization: Bearer $TOKEN"
# → 200 {"status": "PROCESSED", "has_source_document": true, "processing_duration_ms": 8421}
```

Kegagalan konversi **tidak** muncul pada response `process` (tidak ada client
yang menunggu pekerjaan background). Kegagalannya terlihat saat polling:
`status: FAILED` beserta `processing_error_code` (`RPS_PROCESSING_FAILED`) dan
`processing_error_message` — alasan publik yang aman ditampilkan, sedangkan
penyebab teknisnya hanya ada di log server-side.

Runner berjalan *in-process* (Starlette `BackgroundTasks`), sehingga belum tahan
terhadap proses yang mati di tengah konversi. Dua bentengnya: dokumen yang
terlantar boleh diproses ulang setelah `RPS_PROCESSING_LEASE_SECONDS` (default
900 detik), dan antrean pekerjaan yang durable menyusul bersama Agent Run pada
BE-08.

### Idempotency: `file_hash` + `schema_version`

Dokumen dengan `file_hash` dan `schema_version` yang sama **tidak diproses ulang**:

1. unggahan ulang dokumen identik mengembalikan baris yang sudah ada
   (`200`, `deduplicated: true`) alih-alih membuat baris kedua;
2. pemrosesan dokumen yang sudah `PROCESSED` untuk versi skema yang sama
   dijawab `200` + `reused: true` tanpa menjadwalkan konversi lagi.

Meminta pemrosesan dengan `schema_version` **berbeda** justru memproses ulang:
hasil lama tidak berlaku untuk skema baru, dan dokumen mencatat versi yang
benar-benar dipakai.

Konversi yang masih berjalan tidak dapat dijadwalkan ulang (409
`INVALID_REQUEST`), kecuali barisnya sudah lebih tua dari lease — jalan keluar
untuk pemrosesan yang terputus.

### Docling adalah dependensi opsional

Docling menarik `torch` dan model ML (unduhan model pertama kali ±0,5 GB),
sehingga dipasang sebagai *extra* — bukan beban wajib seluruh tim:

```bash
uv sync --extra docling                                  # host
UV_SYNC_ARGS="--extra docling" docker compose build backend   # container
```

Tanpa extra tersebut aplikasi tetap berjalan; `POST /rps/{id}/process` gagal
dengan 500 `RPS_PROCESSING_FAILED` dan pesan server-side yang menyebutkan
perintah pemasangannya. Modul `src/services/rps/docling_converter.py` mengimpor
Docling secara *lazy*, sehingga tidak ada layer lain yang perlu tahu hal ini.

Konfigurasi terkait ada pada `.env.example` (`RPS_*`). Untuk deployment offline,
unduh model lebih dulu dan arahkan `RPS_CONVERTER_ARTIFACTS_PATH`:

```bash
docling-tools models download --output-dir ./var/docling-models
```

### RPS Structured Data Schema (BE-05.3)

`src/schemas/rps_structured.py` adalah kontrak bersama backend dan AI untuk
tahap ekstraksi (BE-08), mengikuti content-schema §6.1/§6.2:

- hierarki capaian pembelajaran eksplisit: **CPL → CPMK → Sub-CPMK**
  (`cpl`/`cpmk`/`sub_cpmk`), karena itulah yang tercantum pada template RPS
  program studi;
- rencana mingguan dengan `week_type` (`regular`/`uts`/`uas`), media
  pembelajaran, dan bobot penilaian `weight_percent` (0–100);
- `extraction` mencatat bagaimana data diperoleh (konverter, model, halaman
  sumber, keyakinan, peringatan);
- seluruh field akademik **opsional** — RPS antar-program studi berbeda-beda,
  dan sistem tidak boleh mengarang nilai yang tidak ada di dokumen;
- `extra="forbid"` pada setiap object: field di luar kontrak adalah kegagalan
  validasi, bukan data yang dibuang diam-diam (§3.2/§3.4);
- `validate_references()` melaporkan rujukan silang yang tidak menemukan sasaran
  (Sub-CPMK → CPMK → CPL dan rujukan mingguan) sebagai **temuan, bukan error**
  (§3.3);
- `RPS_SCHEMA_VERSION` (kini `"2.0"`) menjadi versi skema — terpisah dari content
  version dan dipakai pada kunci idempotency. Naik dari 1.0 ke 2.0 bersifat
  *breaking* (§44): padanan field lamanya `learning_outcomes` → `cpmk` dan
  `objectives` → `sub_cpmk`;
- `to_rps_analysis_payload()` memetakan hasil ekstraksi ke kolom `rps_analyses`
  (data-model §9): CPMK → `learning_outcomes`, Sub-CPMK → `objectives`,
  sedangkan CPL/media/metadata ekstraksi tersimpan utuh pada `raw_analysis`;
- `RPSStructuredData.model_json_schema()` dapat dibagikan ke tim AI sebagai
  JSON Schema (§45).

### Ketetapan yang berlaku untuk modul ini

1. **Berkas disimpan berdasarkan isinya (content-addressed).**
   Path-nya `<owner_id>/<hash[:2]>/<hash>.<ext>` di bawah `RPS_STORAGE_DIR`
   (default `backend/var/rps`, tidak masuk repository). Nama file dari client
   hanya menjadi metadata; ia tidak pernah dipakai membentuk path, dan path
   relatif yang tersimpan di `rps.file_path` diperiksa ulang agar tidak dapat
   keluar dari direktori penyimpanan.
2. **Berkas asli dipertahankan** agar hasil dapat dilacak ke sumbernya
   (data-model §8), dan `source_markdown` disimpan pada kolom `rps` supaya dapat
   dibaca tanpa menyentuh filesystem.
3. **Artefak konversi berada di samping dokumennya**
   (`<hash>/conversion/`): `document.json`, `document.yaml`, `tables.json`, dan
   `conversion.json` (manifest: versi konverter, jumlah tabel, waktu konversi).
   Artefak ditulis **sebelum** status berubah menjadi `PROCESSED`.
4. **Tabel dipisahkan, bukan diratakan.** Tabel RPS (distribusi mingguan, bobot
   penilaian) adalah data akademik; `tables.json` menyimpan baris/kolomnya
   sehingga BE-08 dapat membacanya tanpa mem-parsing Markdown kembali.
5. **Pemrosesan asynchronous (design-api §6.3).** `POST /process` menjawab
   `202` + `PROCESSING` dan konversinya berjalan di background; client memantau
   `GET /rps/{id}`. `agent_run_id` belum ada pada response karena tabel
   `agent_runs` mensyaratkan `course_id` yang baru ada setelah RPS dianalisis
   (data-model §10) — Agent Run menyusul pada BE-08.
6. **Kegagalan konversi tidak menghapus dokumen.** Status menjadi `FAILED`,
   dokumen dapat diproses ulang, dan penyebab sebenarnya hanya dicatat
   server-side. Yang dibaca client saat polling adalah
   `processing_error_code` + `processing_error_message` — alasan publik yang
   ditulis pada titik kegagalannya, bukan pesan library mentah.
7. **Dokumen milik instructor lain menghasilkan 404**, bukan 403 — keberadaan
   RPS orang lain tidak dapat disimpulkan dari perbedaan response.
8. **Validasi berkas berlapis:** ekstensi (mengikuti `RPS_ALLOWED_EXTENSIONS`),
   ukuran (`RPS_MAX_UPLOAD_BYTES`), dan isi (magic bytes) diperiksa sebelum
   apa pun disimpan, sesuai design-api §23.8.

### Di mana komponennya berada

| Komponen | Lokasi |
| :--- | :--- |
| Domain dokumen + lifecycle (`RPSDocument`) | `src/services/rps/domain.py` |
| Operasi aplikasi (unggah, ambil, proses) | `src/services/rps/service.py` |
| Akses tabel `rps` | `src/services/rps/repository.py` |
| Validasi & normalisasi (murni) | `src/services/rps/validation.py` |
| Penyimpanan berkas (port + adapter lokal) | `src/services/rps/storage.py` |
| Port konversi dokumen | `src/services/rps/converter.py` |
| Adapter Docling | `src/services/rps/docling_converter.py` |
| Pemilihan konverter & penyimpanan | `src/services/rps/factory.py` |
| Runner pemrosesan background | `src/services/rps/runner.py` |
| Error domain + kontrak HTTP-nya | `src/services/rps/errors.py` |
| DTO endpoint RPS | `src/schemas/rps.py` |
| RPS Structured Data Schema | `src/schemas/rps_structured.py` |
| Endpoint HTTP | `src/routes/rps.py` |
| Kolom `rps` (`schema_version`, `source_document`, `processing_*`) | `src/models/rps.py` + migrasi `b3c9e14a7f52_*.py`, `c8f4a1d27e93_*.py` |

### Pengujian

```bash
uv run pytest tests/test_rps_structured_schema.py   # kontrak schema (BE-05.3)
uv run pytest tests/test_rps_domain.py              # domain + validasi berkas
uv run pytest tests/test_rps_storage.py             # penyimpanan & path traversal
uv run pytest tests/test_rps_service.py             # unggah, idempotency, kegagalan
uv run pytest tests/test_rps_routes.py              # endpoint (butuh PostgreSQL)
uv run pytest tests/test_rps_runner.py              # runner background (butuh PostgreSQL)
uv run pytest tests/test_rps_docling_converter.py   # adapter Docling

# Konversi Docling sungguhan (opt-in; memakai tests/fixtures/test.pdf dan
# mengunduh model ±0,5 GB saat pertama kali):
RPS_DOCLING_LIVE_TEST=1 uv run pytest tests/test_rps_docling_converter.py -v -s
# Ganti dokumennya bila perlu:
RPS_DOCLING_LIVE_TEST=1 RPS_DOCLING_TEST_PDF=/path/ke/rps.pdf uv run pytest tests/test_rps_docling_converter.py
```

`tests/fixtures/test.pdf` adalah RPS 16 halaman bertemplate program studi yang
dipakai test live di atas; ia juga menjadi bahan verifikasi manual alur
unggah → proses.

`tests/test_rps_routes.py` memakai PostgreSQL (fixture `conftest.db_session`,
default `TEST_DATABASE_URL`), sehingga native enum `rps_status` dan kolom JSONB
benar-benar terpakai. Konverter diganti konverter palsu di sana agar suite tetap
ringan dan deterministik.

---

## ✅ Contoh Penerapan Boundary (Benar vs Salah)

**1. Route handler — benar (tipis, hanya urusan HTTP):**

```python
# src/routes/rps.py  ✅
router = APIRouter(prefix="/api/v1/rps", tags=["RPS"])

@router.post("", response_model=RPSDetailResponse, status_code=201)
async def upload_rps(
    payload: RPSUploadRequest,
    service: RPSService = Depends(get_rps_service),
):
    return await service.create_rps(payload)
```

**Route handler — salah (business logic + akses DB di router):**

```python
# src/routes/rps.py  ❌
@router.post("")
async def upload_rps(payload: RPSUploadRequest, db: AsyncSession = Depends(get_db)):
    if len(payload.content) < 100:                 # aturan bisnis di router
        raise HTTPException(status_code=400, detail="RPS terlalu pendek")
    rps = RPS(title=payload.title)                 # akses DB di router
    db.add(rps)
    await db.commit()
    await db.refresh(rps)
    return RPSDetailResponse.model_validate(rps)
```

**2. Service — benar (logika domain + delegasi data access):**

```python
# src/services/rps_service.py  ✅
class RPSService:
    def __init__(self, session: AsyncSession):
        self.repository = RPSRepository(session)

    async def create_rps(self, payload: RPSUploadRequest) -> RPS:
        self._ensure_minimum_length(payload.content)
        return await self.repository.create(title=payload.title, content=payload.content)

    def _ensure_minimum_length(self, content: str) -> None:
        if len(content) < self.MIN_CONTENT_LENGTH:
            raise RPSValidationError("RPS terlalu pendek")
```

**3. Repository — benar (murni operasi data):**

```python
# src/services/rps_repository.py  ✅
class RPSRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, title: str, content: str) -> RPS:
        rps = RPS(title=title, content=content)
        self._session.add(rps)
        await self._session.commit()
        await self._session.refresh(rps)
        return rps
```

---

## 🧾 Checklist Review Boundary Layer

Gunakan checklist ini saat me-review PR backend:

- [ ] Route handler hanya menangani urusan HTTP: validasi input, memanggil service/controller, dan mengembalikan response.
- [ ] Tidak ada aturan bisnis (percabangan domain, kalkulasi, keputusan workflow) di dalam `routes/` atau `controllers/`.
- [ ] Tidak ada pemanggilan `select` / `add` / `commit` / `execute` maupun import `sqlalchemy` di dalam `routes/`.
- [ ] Seluruh akses database berada di `services/` (langsung atau melalui repository di dalam `services/`).
- [ ] Layer bawah tidak mengimpor layer di atasnya, dan request tidak melompati layer.

---

## 🛠️ Workflow Pengembangan & Testing

### 1. Manajemen Dependensi
Gunakan **`uv`** untuk manajemen environment dan dependensi:
```bash
# Sinkronisasi dependensi
uv sync

# Menambah dependensi baru
uv add <package-name>
```

### 2. Jalankan Server Development
```bash
uv run uvicorn src.main:app --reload
```

### 3. Running Automated Tests
Seluruh pengujian berada di folder `tests/` dan harus dijalankan serta lulus sebelum membuat Pull Request:
```bash
uv run pytest
```

Pengujian yang membutuhkan PostgreSQL (`tests/test_auth_postgres.py`) dijalankan bila database tersedia dan otomatis dilewati bila tidak.

---

## 🐳 Menjalankan dengan Docker

`docker-compose.yml` di root repository menjalankan **PostgreSQL 16 + backend** dengan konfigurasi yang sama untuk seluruh tim, termasuk migrasi Alembic yang dijalankan otomatis saat container start.

```bash
cd ..                          # root repository
docker compose up -d --build
docker compose ps              # db & backend harus berstatus healthy
curl http://127.0.0.1:8000/health
```

Isi folder ini yang terlibat:

| Berkas | Keterangan |
| :--- | :--- |
| `Dockerfile` | `python:3.13-slim` + `uv 0.11.21`; memasang seluruh dependensi (termasuk grup `dev`, agar test suite dapat dijalankan di container); berjalan sebagai user non-root `app` |
| `.dockerignore` | Mengecualikan `.env` (credential tidak pernah masuk image) dan artefak lokal; `.env.example` tetap disertakan karena Settings memakainya sebagai fallback konfigurasi |
| `docker-entrypoint.sh` | Menunggu database siap, menjalankan `alembic upgrade head` (idempotent), lalu mengeksekusi perintah utama |

> **Database dev perlu dibuat ulang sekali** setelah perubahan ini: revisi lama `c182a1549dc6_create_user_entity` digantikan oleh `6f02c577518b_init_schema` + `86ab20d2f2a8_integrate_into_moodle` (histori migrasi ditulis ulang, satu root). Database yang masih tercatat pada revisi lama akan gagal `alembic upgrade head` — hentikan dengan `docker compose down -v` (atau `DROP DATABASE`) lalu `docker compose up -d --build`.

Perintah yang sering dipakai:

```bash
docker compose logs -f backend                              # log aplikasi (uvicorn --reload)
docker compose run --rm backend uv run pytest               # test suite di dalam container
docker compose run --rm backend uv run pytest tests/test_auth_postgres.py
docker compose exec backend uv run alembic upgrade head     # migrasi manual
docker compose exec db psql -U postgres -d lms_moodle_db    # shell database
docker compose down                                         # hentikan service
docker compose down -v                                      # hentikan + hapus data database
```

Catatan:

1. Backend di container menjangkau database lewat nama service `db` (`DB_HOST=db`), bukan `localhost`.
2. Kredensial default mengikuti `backend/.env.example`. Bila menjalankan backend langsung di host, siapkan `backend/.env` dan pastikan `DB_PORT` sama dengan port yang dipublikasikan compose.
3. `./backend/src` dan `./backend/tests` di-mount ke container sehingga perubahan kode langsung terpakai (uvicorn `--reload`); `.venv` di dalam image tidak tertimpa.
4. Port yang sudah dipakai dapat ditimpa: `DB_PORT=5433 APP_PORT=8001 docker compose up -d`.

---

## 🌱 Seed Akun Uji (BE-06.3)

Tim frontend dan backend memakai akun uji yang sama untuk authentication dan
authorization. Seed membuat akun berikut:

| Role | Username | Email | Password |
| :--- | :--- | :--- | :--- |
| `INSTRUCTOR` | `dosen.demo` | `dosen.demo@itk.ac.id` | Dari environment/argumen — **tidak** di-commit |
| `STUDENT` | `11231023` | `11231023@student.itk.ac.id` | Dari environment/argumen — **tidak** di-commit |

Identitas mengikuti konvensi ITK: mahasiswa memakai NIM sebagai username dan
`<NIM>@student.itk.ac.id` sebagai email; dosen memakai alamat berbasis nama,
bukan `<NIP>@dosen.itk.ac.id`.

Password akun uji dibagikan melalui kanal internal tim. Repository tidak
menyimpan password, hash, maupun nilai default-nya.

### Menjalankan seed (backend di host)

Prasyarat: database berjalan dan migrasi sudah diterapkan.

```bash
cd backend
uv run alembic upgrade head

# Disarankan: password lewat environment, tidak muncul di shell history/process list
SEED_INSTRUCTOR_PASSWORD='<password-internal>' \
SEED_STUDENT_PASSWORD='<password-internal>' \
uv run python -m scripts.seed_test_accounts

# Alternatif: script membuatkan password acak dan menampilkannya sekali
uv run python -m scripts.seed_test_accounts --generate-passwords

# Alternatif lain (password dapat terlihat di process list)
uv run python -m scripts.seed_test_accounts \
  --instructor-password '<password-internal>' \
  --student-password '<password-internal>'
```

### Menjalankan seed (Docker Compose)

```bash
docker compose exec backend uv run python -m scripts.seed_test_accounts --generate-passwords

# atau berikan password lewat environment container
docker compose exec \
  -e SEED_INSTRUCTOR_PASSWORD='<password-internal>' \
  -e SEED_STUDENT_PASSWORD='<password-internal>' \
  backend uv run python -m scripts.seed_test_accounts
```

Script aman dijalankan berulang:

- akun dicari berdasarkan email (unik dan stabil), bukan dibuat ulang;
- field yang sudah sesuai tidak diubah;
- password hanya di-hash ulang bila nilainya berbeda dari hash tersimpan;
- role/nama/username yang berbeda diperbarui dan user non-aktif diaktifkan;
- percobaan kedua melaporkan `unchanged` untuk kedua akun.

Konflik identitas tidak ditimpa: bila username akun uji sudah dipakai user lain,
seed berhenti dengan pesan yang aman (tanpa credential) alih-alih mengubah user
tersebut.

### Verifikasi login

```bash
curl -sS -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"11231023@student.itk.ac.id","password":"<password-internal>"}'
```

Identifier dapat berupa username (`11231023`) maupun email
(`11231023@student.itk.ac.id`). Response `200` memuat `access_token`,
`token_type`, dan `user.role` (untuk akun di atas: `INSTRUCTOR` / `STUDENT`).
Panduan authentication lengkap ada di
[`docs/02. design/auth-api-integration.md`](../docs/02.%20design/auth-api-integration.md).

| Komponen | Lokasi |
| :--- | :--- |
| Definisi akun dan operasi seed idempotent | `src/services/seed/test_accounts.py` |
| CLI (environment/argumen/generate password) | `scripts/seed_test_accounts.py` |
| Pengujian, termasuk login melalui API | `tests/test_seed_test_accounts.py` |

Exit code script: `0` berhasil, `1` kegagalan database/seed, `2` konfigurasi
password tidak valid.
