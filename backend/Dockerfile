# syntax=docker/dockerfile:1

# Image backend (FastAPI + SQLAlchemy async + Alembic) untuk lingkungan
# development/parity lewat docker-compose.yml.
#
# Catatan: grup dependensi `dev` sengaja ikut dipasang supaya test suite dapat
# dijalankan di dalam container dengan environment yang sama seperti runtime.
# Image ini bukan image produksi yang di-harden.

FROM python:3.13-slim

# uv dengan versi yang sama seperti yang dipakai tim di host.
COPY --from=ghcr.io/astral-sh/uv:0.11.21 /uv /uvx /bin/

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    UV_CACHE_DIR=/home/app/.cache/uv \
    HOME=/home/app \
    PYTHONPATH=/app

WORKDIR /app

# Manifes dependensi disalin lebih dulu agar layer ini ter-cache selama lockfile
# tidak berubah.
COPY pyproject.toml uv.lock ./
#
# Extra opsional tidak dipasang secara default: `docling` (konversi RPS, BE-05)
# menarik torch dan model ML berukuran ratusan MB, sehingga pemasangannya
# menjadi pilihan operator — bukan beban wajib setiap build maupun CI.
#
#   docker compose build --build-arg UV_SYNC_ARGS="--extra docling" backend
#
# Tanpa extra tersebut aplikasi tetap berjalan; endpoint pemrosesan RPS gagal
# dengan error domain RPS_PROCESSING_FAILED beserta perintah pemasangannya.
ARG UV_SYNC_ARGS=""
RUN uv sync --frozen ${UV_SYNC_ARGS}

# Source code dan konfigurasi. `.env.example` ikut karena Settings memakainya
# sebagai fallback konfigurasi; `.env` asli tidak pernah masuk image
# (lihat .dockerignore) — credential diberikan lewat environment compose.
COPY . .

# Cache uv dibuat sebagai root saat build lalu di-chown ke user aplikasi, agar
# uv tetap dapat memakai cache-nya ketika container berjalan sebagai non-root.
#
# `/app/var` (penyimpanan dokumen RPS, BE-05) ikut dibuat di sini: volume bernama
# pada compose mewarisi isi dan kepemilikan direktori image, sehingga tanpa ini
# volume baru akan dimiliki root dan backend (uid 1000) gagal menulis dokumen.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.cache/uv /app/var/rps \
    && chown -R app:app /app /home/app

USER app

EXPOSE 8000

# Entry point menjalankan migrasi database terlebih dahulu (idempotent).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
