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
│   │   ├── auth.py               # POST /auth/login, GET /auth/me
│   │   ├── health.py
│   │   └── __init__.py           # Registri router terpusat (api_router)
│   ├── controllers/              # HTTP Request Orchestrator / Data Mapping Layer
│   ├── services/                 # Core Business Logic, Data Access, & External APIs
│   │   ├── auth/                 # Authentication: kredensial, token, AuthService
│   │   ├── user/                 # Domain User/Role, UserService, UserRepository
│   │   ├── llm/                  # Integrasi penyedia LLM
│   │   └── dependencies.py       # Dependency provider untuk routes
│   ├── models/                   # Database Entities / ORM Models (SQLAlchemy)
│   ├── schemas/                  # Request & Response DTOs / Data Validation (Pydantic)
│   │   └── auth.py
│   ├── middlewares/              # FastAPI Middlewares (Error Handler, Auth, CORS)
│   │   └── error_handlers.py     # Pemetaan error domain → response HTTP
│   ├── utils/                    # Helper functions & pure utilities
│   └── main.py                   # FastAPI Application Entry Point
├── tests/                        # Automated unit & integration tests (pytest)
│   ├── conftest.py               # Fixture bersama (session SQLite in-memory)
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
| `GET` | `/api/v1/auth/me` | Mengembalikan current user; membutuhkan header `Authorization: Bearer <access_token>` |

`username` pada login adalah **email** user (email adalah identity attribute pada data model; User tidak memiliki atribut username terpisah).

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
