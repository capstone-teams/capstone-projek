# Backend Module

Folder ini berisi source code dan konfigurasi untuk service backend.

## Structure Overview
```text
backend/
├── src/
│   ├── config/
│   ├── controllers/
│   ├── middlewares/
│   ├── models/
│   ├── routes/
│   ├── services/
│   └── utils/
├── tests/
├── pyproject.toml
├── uv.lock
└── README.md
```

## Baseline Setup
- Penamaan dan struktur modul mengikuti standar arsitektur backend yang disepakati.
- Variabel lingkungan wajib mengacu pada `.env.example` di root repository.
- Manajemen dependensi menggunakan **uv**:
  - Install dependensi: `uv sync`
  - Run tests: `uv run pytest`

