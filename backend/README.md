# Backend Module

Folder ini berisi *source code*, konfigurasi, dan pengujian untuk service backend yang dibangun menggunakan **FastAPI**, **SQLAlchemy**, dan **Pydantic**.

---

## 🏗️ Structure Overview

```text
backend/
├── alembic/                      # Skrip & histori migrasi database (Alembic)
│   ├── versions/                 # File revisi migrasi skema DB (.py)
│   └── env.py                    # Konfigurasi runtime environment Alembic
├── alembic.ini                   # File konfigurasi utama Alembic
├── src/                          # Source code utama aplikasi
│   ├── config/                   # Konfigurasi aplikasi, env vars, & koneksi DB
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── routes/                   # Definition Endpoint API & HTTP Router (FastAPI)
│   │   ├── __init__.py           # Registri & agregator router (/api/v1)
│   │   └── health.py             # Endpoint root & health check
│   ├── controllers/              # HTTP Request Orchestrator / Data Mapping Layer
│   │   └── __init__.py
│   ├── services/                 # Core Business Logic, Data Access, & External APIs
│   │   └── __init__.py
│   ├── models/                   # Database Entities / ORM Models (SQLAlchemy)
│   │   └── __init__.py
│   ├── schemas/                  # Request & Response DTOs / Data Validation (Pydantic)
│   │   └── __init__.py
│   ├── middlewares/              # FastAPI Middlewares (Error Handler, Auth, CORS)
│   │   └── __init__.py
│   ├── utils/                    # Helper functions & pure utilities
│   │   └── __init__.py
│   └── main.py                   # FastAPI Application Entry Point
├── tests/                        # Automated unit & integration tests (pytest)
│   ├── test_config.py
│   └── test_main.py
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

Aturan Repository:

1. Repository **hanya** berisi operasi data (query & mutasi) — tanpa aturan bisnis, kalkulasi domain, atau percabangan workflow.
2. Repository hanya boleh dipanggil oleh `services/`. `routes/` dan `controllers/` **dilarang** memanggil repository secara langsung.
3. Jika sebuah fitur belum membutuhkan query kompleks, repository **tidak perlu dibuat**. Service boleh langsung memakai `Session` — yang penting tanggung jawab tersebut tetap berada di layer service, bukan di router.

---

## 🧩 Konvensi Pembuatan Module / Domain Baru

Struktur direktori backend **bersifat tetap** (lihat bagian *Structure Overview*). Karena itu "module" atau "domain" di proyek ini **bukan** direktori baru, melainkan sebuah *kesatuan file* yang tersebar pada layer yang sudah ada. Konvensi ini memastikan setiap anggota tim membuat domain baru dengan pola yang sama, tanpa menentukan strukturnya sendiri-sendiri.

### 1. Komponen Sebuah Domain

| Komponen | Lokasi File | Wajib? | Contoh |
| :--- | :--- | :--- | :--- |
| **Router** | `src/routes/<domain>.py` | Wajib | `src/routes/rps.py` |
| **Schema** | `src/schemas/<domain>.py` | Wajib jika ada request/response body | `src/schemas/rps.py` |
| **Service** | `src/services/<domain>_service.py` | Wajib | `src/services/rps_service.py` |
| **Model** | `src/models/<domain>.py` | Wajib jika domain punya tabel | `src/models/rps.py` |
| **Repository** | `src/services/<domain>_repository.py` | Opsional (lihat bagian *Repository / Data Access*) | `src/services/rps_repository.py` |
| **Controller** | `src/controllers/<domain>.py` | Opsional (lihat bagian *Tanggung Jawab Setiap Layer*) | `src/controllers/rps.py` |
| **Test** | `tests/test_<domain>.py` | Wajib | `tests/test_rps.py` |

Aturan:

1. **Tidak semua komponen wajib ada.** Buat komponen hanya jika domain benar-benar membutuhkannya. Domain yang hanya membaca data dari sistem eksternal (contoh: daftar course dari Moodle) tidak perlu `models/` maupun repository.
2. **Dilarang membuat direktori baru per domain** (contoh: `src/rps/`, `src/modules/rps/`, `src/routes/rps/`). Semua file domain tetap berada pada layer masing-masing.
3. **Dilarang membuat direktori `repositories/`.** Data access berada di `src/services/`.
4. Satu domain diwakili oleh **satu file per layer**, bukan satu direktori. Jika salah satu file mulai terlalu besar atau menangani lebih dari satu entity, pecah berdasarkan **sub-domain**, bukan dengan menambah layer baru: `src/services/rps_analysis_service.py`.

### 2. Aturan Penamaan

| Elemen | Konvensi | Contoh |
| :--- | :--- | :--- |
| File router | `<domain>.py` (snake_case) | `src/routes/rps.py` |
| Variabel router | `router` | `router = APIRouter(prefix="/rps", tags=["RPS"])` |
| File service | `<domain>_service.py` | `src/services/rps_service.py` |
| Kelas service | `<Domain>Service` (PascalCase) | `class RPSService` |
| File repository | `<domain>_repository.py` | `src/services/rps_repository.py` |
| Kelas repository | `<Domain>Repository` | `class RPSRepository` |
| File model | `<domain>.py` | `src/models/rps.py` |
| Kelas model | `<Domain>` (tunggal, PascalCase) | `class RPS(Base)` |
| Nama tabel | plural snake_case | `__tablename__ = "rps"` |
| File schema | `<domain>.py` | `src/schemas/rps.py` |
| Kelas schema | `<Domain><Kegunaan><Request\|Response>` | `RPSUploadRequest`, `RPSDetailResponse` |
| File test | `test_<domain>.py` | `tests/test_rps.py` |

### 3. Prefix Endpoint Domain

Prefix versi API (`/api/v1`) **hanya** dimiliki oleh `api_router` di `src/routes/__init__.py`. File router domain cukup menuliskan prefix domainnya sendiri:

| `APIRouter(prefix=...)` di `src/routes/<domain>.py` | URL akhir |
| :--- | :--- |
| `prefix="/rps"` | `/api/v1/rps` |
| `prefix="/courses"` | `/api/v1/courses` |

Menuliskan `/api/v1` di dalam file router domain (`prefix="/api/v1/rps"` ❌) menghasilkan URL ganda (`/api/v1/api/v1/rps`).

### 4. Registrasi Router Domain

Router domain didaftarkan di **satu tempat**: `src/routes/__init__.py`.

```python
# src/routes/__init__.py
from fastapi import APIRouter

from src.routes.health import router as health_router
from src.routes.rps import router as rps_router

API_V1_PREFIX = "/api/v1"

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(rps_router)
```

`src/main.py` **tidak perlu diubah** saat menambah domain — ia hanya menyertakan `health_router` (endpoint infrastruktur, tanpa prefix versi) dan `api_router`.

### 5. Langkah Membuat Domain Baru

Contoh domain `rps`:

1. **Schema** — buat `src/schemas/rps.py` berisi DTO request/response (`RPSUploadRequest`, `RPSDetailResponse`).
2. **Model** — buat `src/models/rps.py` berisi ORM model, hanya jika domain punya tabel.
3. **Repository** *(opsional)* — buat `src/services/rps_repository.py` jika query mulai panjang/berulang atau dipakai lebih dari satu service.
4. **Service** — buat `src/services/rps_service.py` berisi seluruh logika bisnis domain.
5. **Router** — buat `src/routes/rps.py` dengan `router = APIRouter(prefix="/rps", tags=["RPS"])`. Handler hanya memvalidasi input, memanggil service, dan mengembalikan response.
6. **Registrasi** — tambahkan satu baris di `src/routes/__init__.py`: `api_router.include_router(rps_router)`.
7. **Test** — buat `tests/test_rps.py` (minimal: happy path endpoint dan aturan bisnis utama service).
8. **Verifikasi** — jalankan `uv run pytest`, lalu pastikan endpoint muncul di `/docs` dengan URL `/api/v1/<domain>`.

### 6. Kerangka File per Layer

```python
# src/schemas/rps.py — DTO Pydantic saja
from pydantic import BaseModel


class RPSUploadRequest(BaseModel):
    title: str
    content: str


class RPSDetailResponse(BaseModel):
    id: int
    title: str
```

```python
# src/models/rps.py — ORM model saja
from sqlalchemy.orm import Mapped, mapped_column

from src.config.database import Base  # Base disediakan oleh milestone BE-02


class RPS(Base):
    __tablename__ = "rps"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    content: Mapped[str]
```

Kerangka `routes/`, `services/`, dan repository sudah dicontohkan pada bagian *Contoh Penerapan Boundary* di bawah, sehingga tidak diulang di sini.

> **Catatan (akan difinalkan pada BE-02):** penempatan dependency provider seperti `get_rps_service(...)` belum ditetapkan karena bergantung pada `AsyncSession` / `get_db` dari database foundation. Ingat bahwa `src/routes/` **dilarang** mengimpor `sqlalchemy` maupun `Session`, sehingga provider tidak boleh dituliskan sembarangan di dalam file router.

### 7. Checklist Penambahan Domain

- [ ] Seluruh file domain berada pada layer yang benar, dan tidak ada direktori baru per domain.
- [ ] File router bernama `src/routes/<domain>.py` dan prefix `/api/v1` tidak ditulis dua kali.
- [ ] Router terdaftar tepat satu kali melalui `api_router` di `src/routes/__init__.py`.
- [ ] `src/main.py` tidak diubah dan tidak ada route yang didefinisikan di luar `src/routes/`.
- [ ] Tidak ada query database di dalam `routes/`, dan layer bawah tidak mengimpor layer di atasnya.
- [ ] Domain baru memiliki test pada `tests/test_<domain>.py`.

---

## ✅ Contoh Penerapan Boundary (Benar vs Salah)

**1. Route handler — benar (tipis, hanya urusan HTTP):**

```python
# src/routes/rps.py  ✅
router = APIRouter(prefix="/rps", tags=["RPS"])   # prefix /api/v1 dimiliki api_router

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
