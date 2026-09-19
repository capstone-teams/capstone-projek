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
│   │   └── __init__.py
│   ├── controllers/              # HTTP Request Orchestrator / Data Mapping Layer
│   │   └── __init__.py
│   ├── services/                 # Core Business Logic, Data Access, & External APIs (LLM, Moodle)
│   │   └── llm/
│   ├── models/                   # Database Entities / ORM Models (SQLAlchemy)
│   │   └── __init__.py
│   ├── schemas/                  # Request & Response DTOs / Data Validation (Pydantic)
│   │   └── __init__.py
│   ├── middlewares/              # FastAPI Middlewares (Error Handler, Auth, CORS)
│   │   └── error_handlers.py
│   ├── utils/                    # Helper functions & pure utilities
│   │   └── __init__.py
│   └── main.py                   # FastAPI Application Entry Point
├── tests/                        # Automated unit & integration tests (pytest)
│   ├── test_config.py
│   ├── test_llm_live.py
│   ├── test_llm_provider.py
│   ├── test_llm_service.py
│   └── test_main.py
├── pyproject.toml                # Konfigurasi dependensi & tools (uv)
├── pytest.ini                    # Konfigurasi test runner pytest
├── uv.lock                       # Lockfile dependensi uv
└── README.md                     # Dokumentasi arsitektur backend
```

---

## 🎯 Tanggung Jawab Setiap Layer (Separation of Concerns)

Untuk menjaga konsistensi dan mencegah duplikasi fungsi antar layer, seluruh anggota tim backend **wajib** mematuhi pembagian peran berikut:

| Layer / Direktori | Responsibilitas Utama | Yang BOLEH Dilocate | Yang TIDAK BOLEH Dilocate |
| :--- | :--- | :--- | :--- |
| **`src/main.py`** | Application Entry Point | Inisialisasi FastAPI app, registrasi router & middleware global, event lifespan (startup/shutdown). | Logika bisnis, query database, definisi route individual. |
| **`src/config/`** | System Configuration & Core Setup | Pydantic `BaseSettings` (`settings.py`), insialisasi Database Engine/Session, environment constants. | Logika bisnis, HTTP error response formatting. |
| **`src/routes/`** | API Router & HTTP Request Handling | Definisi endpoint HTTP (GET, POST, PUT, DELETE), validasi input URL/Header (`Depends`), memanggil Controller/Service, mengembalikan response HTTP. | Direct SQL / ORM Queries, transaksi database, logika integrasi pihak ketiga. |
| **`src/controllers/`** | Request Orchestrator *(Opsional)* | Menghubungkan request dari route ke satu atau beberapa service, formatting data response DTO. | Menulis query DB langsung, logika bisnis inti yang kompleks. |
| **`src/services/`** | Business Logic & External Integrations | Seluruh logika bisnis aplikasi, query/mutasi DB via SQLAlchemy Session, integrasi LLM (OpenAI/Gemini), integrasi Moodle API. | Direct HTTP Request/Response handling, Pydantic HTTP error raising secara mentah. |
| **`src/models/`** | Database Entities (SQLAlchemy) | Pemetaan tabel database, kolom, tipe data DB, dan relasi antar tabel (Foreign Keys, Relationships). | Validasi HTTP Request Body, Pydantic models. |
| **`src/schemas/`** | Data Transfer Objects (Pydantic) | Validasi struktur data Request Body, Query Params, dan Response Body (DTO). serialization & deserialization JSON. | Relasi ORM database, query database. |
| **`src/middlewares/`** | Cross-cutting HTTP Concerns | Interceptor request/response, global exception handler (`error_handlers.py`), CORS headers, authentication JWT middleware. | Logika spesifik domain bisnis. |
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
   - `services/` menampung logika yang *stateful* atau memiliki context domain (DB, LLM, Moodle).
   - `utils/` menampung fungsi murni (*stateless*) yang tidak terikat pada domain bisnis tertentu.

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
