#!/usr/bin/env bash
#
# Entry point container backend:
#   1. menunggu database siap (compose sudah memakai healthcheck, retry ini
#      hanya jaring pengaman),
#   2. menerapkan migrasi Alembic (idempotent),
#   3. menjalankan perintah utama (default: uvicorn).
#
# Pemakaian:
#   docker compose up -d --build              # migrasi + server
#   docker compose run --rm backend uv run pytest
#   docker compose run --rm backend uv run alembic downgrade -1

set -euo pipefail

MIGRATION_ATTEMPTS=5

echo "==> Menerapkan migrasi database (alembic upgrade head)"
attempt=1
until uv run alembic upgrade head; do
    if [ "${attempt}" -ge "${MIGRATION_ATTEMPTS}" ]; then
        echo "!! Migrasi gagal setelah ${MIGRATION_ATTEMPTS} percobaan." >&2
        echo "!! Pastikan database terjangkau pada DB_HOST=${DB_HOST:-<belum diset>} DB_PORT=${DB_PORT:-<belum diset>}." >&2
        exit 1
    fi
    echo "==> Database belum siap, percobaan ulang (${attempt}/${MIGRATION_ATTEMPTS}) dalam 2 detik"
    attempt=$((attempt + 1))
    sleep 2
done

echo "==> Menjalankan: $*"
exec "$@"
