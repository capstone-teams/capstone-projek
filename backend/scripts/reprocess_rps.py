"""Proses ulang RPS lama yang belum memiliki JSON hasil Docling (BE-13).

Sebelum BE-13, hasil konversi disimpan sebagai Markdown. Setelah kolom
``source_markdown`` dihapus (DL-008), baris lama yang berstatus ``PROCESSED``
tetapi tidak memiliki ``source_document`` tidak lagi dianggap selesai oleh
idempotency. Script ini memilih baris tersebut dan menjalankan ulang pipeline
konversi Docling untuk masing-masing dokumen.

Pemakaian (dari folder ``backend/``)::

    # lihat berapa dokumen yang akan diproses, tanpa menyentuh Docling
    uv run python -m scripts.reprocess_rps --dry-run

    # proses ulang seluruh baris format lama
    uv run python -m scripts.reprocess_rps

    # batasi jumlah dokumen (berguna saat mencoba di lingkungan bersama)
    uv run python -m scripts.reprocess_rps --limit 5

Prasyarat: migrasi sudah diterapkan (``uv run alembic upgrade head``), extra
Docling terpasang (``uv sync --extra docling``), dan model Docling tersedia.
Dokumen yang gagal dikonversi dicatat sebagai ``FAILED`` pada barisnya dan
dilaporkan oleh script tanpa menghentikan dokumen berikutnya.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError

from src.config.database import dispose_engine, get_session_factory
from src.models.rps import RPS as RPSEntity
from src.services.rps.enums import RPSStatus
from src.services.rps.errors import RPSDomainError
from src.services.rps.service import RPSService

__all__ = ["ReprocessReport", "main", "reprocess_legacy_rps"]

EXIT_OK = 0
EXIT_FAILURE = 1


@dataclass(slots=True)
class ReprocessReport:
    """Ringkasan satu kali eksekusi proses ulang."""

    selected: int = 0
    processed: int = 0
    failed: int = 0
    errors: list[tuple[str, str]] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        return EXIT_OK if self.failed == 0 else EXIT_FAILURE


async def reprocess_legacy_rps(
    *,
    dry_run: bool = False,
    limit: int | None = None,
    session_factory: Callable[[], Any] | None = None,
    service_factory: Callable[[Any], Any] | None = None,
) -> ReprocessReport:
    """Konversi ulang baris ``PROCESSED`` yang belum punya ``source_document``.

    ``session_factory`` dan ``service_factory`` dapat diganti pengujian tanpa
    menyentuh database atau Docling sungguhan. Setiap dokumen memakai session
    baru supaya kegagalan satu baris tidak merusak transaksi baris berikutnya.
    """
    if limit is not None and limit < 1:
        raise ValueError("limit harus lebih besar dari 0")

    session_factory = session_factory or get_session_factory()
    service_factory = service_factory or RPSService.from_session

    statement = (
        select(RPSEntity.id, RPSEntity.owner_id)
        .where(
            RPSEntity.status == RPSStatus.PROCESSED,
            # Baris lama dapat menyimpan ketiadaan hasil sebagai SQL NULL
            # (kolom baru pada migrasi) maupun JSON null (nilai yang ditulis
            # aplikasi sebelum BE-13).
            or_(
                RPSEntity.source_document.is_(None),
                RPSEntity.source_document == JSONB.NULL,
            ),
        )
        .order_by(RPSEntity.created_at)
    )
    if limit is not None:
        statement = statement.limit(limit)

    async with session_factory() as session:
        rows = list((await session.execute(statement)).all())

    report = ReprocessReport(selected=len(rows))
    if dry_run:
        return report

    for rps_id, owner_id in rows:
        try:
            async with session_factory() as session:
                await service_factory(session).process_rps(
                    rps_id=rps_id, owner_id=owner_id
                )
        except (RPSDomainError, SQLAlchemyError) as exc:
            report.failed += 1
            report.errors.append((rps_id, _describe(exc)))
        else:
            report.processed += 1

    return report


def build_parser() -> argparse.ArgumentParser:
    """Parser argumen CLI."""
    parser = argparse.ArgumentParser(
        prog="python -m scripts.reprocess_rps",
        description=(
            "Konversi ulang RPS lama (format Markdown) menjadi JSON Docling "
            "pada source_document."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="hanya tampilkan jumlah dokumen yang akan diproses",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="proses paling banyak N dokumen",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point ``python -m scripts.reprocess_rps``."""
    args = build_parser().parse_args(argv)
    if args.limit is not None and args.limit < 1:
        print("--limit harus lebih besar dari 0", file=sys.stderr)
        return EXIT_FAILURE

    try:
        report = asyncio.run(_run(dry_run=args.dry_run, limit=args.limit))
    except SQLAlchemyError as exc:
        print(f"gagal mengakses database: {type(exc).__name__}", file=sys.stderr)
        return EXIT_FAILURE

    _print_report(report, dry_run=args.dry_run)
    return report.exit_code


async def _run(*, dry_run: bool, limit: int | None) -> ReprocessReport:
    """Jalankan proses ulang lalu tutup pool koneksi pada loop yang sama."""
    try:
        return await reprocess_legacy_rps(dry_run=dry_run, limit=limit)
    finally:
        await dispose_engine()


def _print_report(report: ReprocessReport, *, dry_run: bool) -> None:
    if dry_run:
        print(f"{report.selected} dokumen format lama akan diproses ulang.")
        return

    print(
        f"selesai: {report.processed} diproses, {report.failed} gagal, "
        f"dari {report.selected} dokumen."
    )
    for rps_id, reason in report.errors:
        print(f"  - {rps_id}: {reason}", file=sys.stderr)


def _describe(exc: Exception) -> str:
    """Alasan ringkas yang aman ditampilkan pada ringkasan CLI."""
    if isinstance(exc, RPSDomainError):
        return exc.public_reason
    return type(exc).__name__


if __name__ == "__main__":
    raise SystemExit(main())
