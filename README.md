# Agentic AI untuk Mengisi Konten Pembelajaran Moodle

Sistem berbasis **Agentic AI** yang membantu dosen mengubah **RPS (Rencana Pembelajaran Semester)** menjadi struktur course dan konten pembelajaran yang siap dieksekusi ke **Moodle** — mulai dari memahami RPS, menyusun perencanaan course, menghasilkan konten, validasi, review dosen, hingga eksekusi ke Moodle.

Proyek Capstone — Institut Teknologi Kalimantan (ITK).

> **Dokumen ini untuk siapa?** Developer yang baru bergabung. Bagian *Quick Start*, *Struktur Repository*, dan *Mulai dari Mana* sudah cukup untuk menjalankan backend dan mengetahui di mana setiap hal berada. Detail arsitektur backend ada di [`backend/README.md`](backend/README.md).

---

## 📌 Status Pengembangan

| Area | Status |
| :--- | :--- |
| Backend — struktur, layer separation, entry point, konfigurasi | Tersedia (milestone **BE-01**) |
| Backend — database foundation (Model, Session, Alembic) | Belum — milestone **BE-02** |
| Backend — autentikasi & authorization | Belum — milestone **BE-03** |
| Backend — integrasi Moodle | Belum — milestone **BE-04** |
| Frontend | Belum ada source code, baru [struktur folder](frontend/README.md) |

---

## ✅ Prasyarat

- **Python 3.13+** — lihat `backend/.python-version`
- **[uv](https://docs.astral.sh/uv/)** — manajemen dependensi & virtual environment
- **PostgreSQL** — dibutuhkan mulai milestone BE-02; belum diperlukan untuk menjalankan backend saat ini

---

## 🚀 Quick Start (Backend)

```bash
git clone https://github.com/capstone-teams/capstone-projek.git
cd capstone-projek/backend

# 1. Sinkronisasi dependensi (sekaligus membuat .venv)
uv sync

# 2. Siapkan environment variable
cp .env.example .env        # lalu sesuaikan nilainya bila diperlukan

# 3. Jalankan server development
uv run uvicorn src.main:app --reload
```

Server berjalan di `http://127.0.0.1:8000`:

| URL | Keterangan |
| :--- | :--- |
| `/` | Menandai service backend berjalan |
| `/health` | Liveness probe |
| `/docs` | Dokumentasi API interaktif (Swagger UI, dihasilkan otomatis dari OpenAPI) |

Menjalankan test:

```bash
cd backend
uv run pytest
```

Seluruh test wajib lulus sebelum membuat Pull Request.

---

## 🗂️ Struktur Repository

```text
capstone-projek/
├── backend/            # Service backend (FastAPI + SQLAlchemy + Pydantic)
│   ├── src/            # Source code aplikasi
│   ├── tests/          # Unit & integration test (pytest)
│   └── README.md       # Dokumentasi arsitektur backend
├── frontend/           # Antarmuka pengguna (belum ada source code)
│   └── README.md
├── docs/               # Dokumentasi proyek
│   ├── 01. project-charter/
│   ├── 02. design/
│   ├── 03. quality-plan/
│   └── 04. workflow/
├── .github/            # Template issue & Pull Request
├── aturan.md           # Aturan kolaborasi: branch, commit, issue, PR, review
└── README.md           # File ini
```

---

## 🏛️ Arsitektur Backend (Ringkas)

Backend memisahkan tanggung jawab per layer, dengan aliran dependency **satu arah (ke bawah)**:

```text
HTTP Request
     │
     ▼
src/routes/         ── kontrak HTTP saja: endpoint, validasi input, response
     │
     ▼
src/controllers/    ── opsional: orkestrasi request & data mapping
     │
     ▼
src/services/       ── logika bisnis; satu-satunya layer pemegang Session database
     │                 (data access / repository opsional, berada di dalam services/)
     ▼
src/models/         ── ORM model + PostgreSQL
```

Aturan yang paling sering dilanggar:

1. Layer bawah **dilarang** mengimpor layer di atasnya, dan request **tidak boleh melompati layer**.
2. `src/routes/` tidak boleh menyentuh database — tidak ada `sqlalchemy`, `Session`, maupun query di dalam router.
3. Router didaftarkan secara terpusat di `src/routes/__init__.py`, dan endpoint bisnis berada di bawah prefix `/api/v1`.
4. `src/main.py` hanya merakit aplikasi (`create_app()`) — tanpa logika bisnis dan tanpa definisi route individual.

Penjelasan lengkap — tabel tanggung jawab tiap layer, aturan import antar-layer, kebijakan repository, konvensi pembuatan module baru, contoh benar vs salah, serta checklist review PR — ada di **[`backend/README.md`](backend/README.md)**.

---

## 🧭 Mulai dari Mana?

Urutan bacaan yang disarankan untuk developer baru:

| # | Dokumen | Isi |
| :--- | :--- | :--- |
| 1 | [`README.md`](README.md) | Gambaran proyek & cara menjalankan (file ini) |
| 2 | [`aturan.md`](aturan.md) | Aturan kolaborasi: branch, commit, issue, PR, code review |
| 3 | [`docs/04. workflow/development-workflow.md`](docs/04.%20workflow/development-workflow.md) | Alur kerja Git detail & branch protection |
| 4 | [`docs/01. project-charter/project-charter.md`](docs/01.%20project-charter/project-charter.md) | Tujuan, ruang lingkup, dan konteks proyek |
| 5 | [`backend/README.md`](backend/README.md) | Arsitektur backend & konvensi penulisan kode |
| 6 | `backend/tests/` | Contoh nyata cara tiap layer diuji |

---

## 🤝 Alur Kontribusi (Ringkas)

1. Ambil issue dari GitHub Project, lalu buat branch dari **`develop`** dengan format `<type>/<short-description>` (contoh: `feature/moodle-integration`, `docs/api-guide`).
2. Commit menggunakan **Conventional Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
3. Pastikan `uv run pytest` lulus dan tidak ada credential/secret yang ikut ter-commit.
4. Buka Pull Request ke `develop` memakai template yang tersedia, dan cantumkan `Closes #<nomor-issue>`.
5. PR membutuhkan minimal **1 approval**. Direct push ke `main` dan `develop` dilarang.

Aturan lengkap: [`aturan.md`](aturan.md) dan [`docs/04. workflow/development-workflow.md`](docs/04.%20workflow/development-workflow.md).

---

## 📚 Referensi Desain & Perencanaan

- [`docs/02. design/prd.md`](docs/02.%20design/prd.md) — Product Requirements Document
- [`docs/02. design/design-api.md`](docs/02.%20design/design-api.md) — spesifikasi API `/api/v1`
- [`docs/02. design/data-model.md`](docs/02.%20design/data-model.md) — model data
- [`docs/02. design/agent-design.md`](docs/02.%20design/agent-design.md) — desain agent
- [`docs/02. design/moodle-integration.md`](docs/02.%20design/moodle-integration.md) — integrasi Moodle
- [`docs/02. design/content-schema.md`](docs/02.%20design/content-schema.md) — skema konten pembelajaran
- [`docs/02. design/design-system.md`](docs/02.%20design/design-system.md) — design system frontend
- [`docs/03. quality-plan/quality-plan.md`](docs/03.%20quality-plan/quality-plan.md) — rencana kualitas
- [`backend/README.md`](backend/README.md) — arsitektur backend
- [`frontend/README.md`](frontend/README.md) — struktur frontend
