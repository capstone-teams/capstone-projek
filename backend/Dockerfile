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
RUN uv sync --frozen

# Source code dan konfigurasi. `.env.example` ikut karena Settings memakainya
# sebagai fallback konfigurasi; `.env` asli tidak pernah masuk image
# (lihat .dockerignore) — credential diberikan lewat environment compose.
COPY . .

# Cache uv dibuat sebagai root saat build lalu di-chown ke user aplikasi, agar
# uv tetap dapat memakai cache-nya ketika container berjalan sebagai non-root.
RUN chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 app \
    && mkdir -p /home/app/.cache/uv \
    && chown -R app:app /app /home/app

USER app

EXPOSE 8000

# Entry point menjalankan migrasi database terlebih dahulu (idempotent).
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD [".venv/bin/uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
