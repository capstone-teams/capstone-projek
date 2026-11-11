"""Aktifkan dan buktikan akses mahasiswa ke course hasil eksekusi (BE-16.3).

Dipakai untuk demo student access setelah course plan dieksekusi ke Moodle:

1. mendaftarkan mahasiswa uji (bawaan ``mhs.uji``) ke course target sebagai student;
2. memeriksa course dan section mingguan terlihat oleh mahasiswa (``--show-hidden``
   menampilkan yang tersembunyi);
3. login sebagai mahasiswa terdaftar dan membandingkan section yang terlihat dengan
   section mingguan course;
4. login sebagai mahasiswa yang tidak terdaftar (bawaan ``mhs.uji2``) dan memastikan
   Moodle menolaknya.

Sejak BE-21.3 setiap activity hasil eksekusi FULL (page, url, assignment, quiz)
juga diperiksa: visibilitasnya, dibuka oleh mahasiswa terdaftar, dan ditolak bagi
mahasiswa yang tidak terdaftar. ``--start-quiz`` benar-benar memulai attempt quiz
sebagai mahasiswa terdaftar lalu langsung menyelesaikannya; gunakan hanya pada
course uji karena attempt tersebut tersimpan di Moodle.

Contoh (dari folder ``backend``)::

    MOODLE_STUDENT_PASSWORD='...' MOODLE_STUDENT2_PASSWORD='...' \\
    uv run python -m scripts.verify_student_access --course-id 42

Username dapat diganti lewat ``MOODLE_STUDENT_USERNAME`` dan
``MOODLE_STUDENT2_USERNAME``; password **wajib** dari environment dan tidak
pernah ditampilkan. Akun dibuat lebih dulu dengan
``scripts.setup_moodle_test_accounts``. Exit code 0 berarti student access
terbukti, 1 berarti ada pemeriksaan yang gagal, 2 berarti konfigurasi atau akun
belum siap.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Mapping, Sequence

from src.config.settings import settings
from src.services.moodle_client import MoodleClient
from src.services.moodle_exceptions import MoodleError
from src.services.moodle_integration_service import MoodleIntegrationService
from src.services.moodle_student_access import (
    ACTIVITY_LABELS,
    MoodleStudentAccessService,
    StudentAccessReport,
    StudentAccessSetupError,
)

ENV_STUDENT_USERNAME = "MOODLE_STUDENT_USERNAME"
ENV_STUDENT_PASSWORD = "MOODLE_STUDENT_PASSWORD"
ENV_OTHER_USERNAME = "MOODLE_STUDENT2_USERNAME"
ENV_OTHER_PASSWORD = "MOODLE_STUDENT2_PASSWORD"
DEFAULT_STUDENT = "mhs.uji"
DEFAULT_OTHER_STUDENT = "mhs.uji2"


def student_credentials(
    env: Mapping[str, str],
) -> tuple[tuple[str, str], tuple[str, str]]:
    """``(username, password)`` mahasiswa terdaftar dan tidak terdaftar dari environment."""
    missing = [
        name
        for name in (ENV_STUDENT_PASSWORD, ENV_OTHER_PASSWORD)
        if not env.get(name, "").strip()
    ]
    if missing:
        raise StudentAccessSetupError(
            f"Isi {' dan '.join(missing)} (password akun dari bagian 8.2 panduan setup)."
        )
    enrolled = (
        env.get(ENV_STUDENT_USERNAME, "").strip() or DEFAULT_STUDENT,
        env[ENV_STUDENT_PASSWORD],
    )
    other = (
        env.get(ENV_OTHER_USERNAME, "").strip() or DEFAULT_OTHER_STUDENT,
        env[ENV_OTHER_PASSWORD],
    )
    if enrolled[0].lower() == other[0].lower():
        raise StudentAccessSetupError(
            "Mahasiswa terdaftar dan tidak terdaftar harus akun yang berbeda."
        )
    return enrolled, other


def _line(ok: bool, text: str) -> str:
    return f"  [{'OK' if ok else 'GAGAL'}] {text}"


def _activity_lines(report: StudentAccessReport) -> list[str]:
    """Satu baris per activity yang dibuka mahasiswa terdaftar (BE-21.3)."""
    lines = []
    hidden = set(report.visibility.hidden_activities)
    for item in report.visibility.activities:
        if item.moodle_module_id in hidden:
            lines.append(
                _line(
                    False,
                    f"Minggu {item.section_number} - {item.modname} '{item.name}' tersembunyi (pakai --show-hidden)",
                )
            )
    for access in report.enrolled.activities:
        label = ACTIVITY_LABELS.get(access.modname, access.modname)
        text = f"Minggu {access.section_number} - {label} '{access.name}'"
        if not access.opened:
            lines.append(_line(False, f"{text} gagal dibuka ({access.error_code})"))
        elif access.attempt_requested:
            detail = (
                "attempt dimulai lalu diselesaikan"
                if access.attempt_started
                else f"attempt gagal dimulai ({access.error_code})"
            )
            lines.append(_line(access.attempt_started, f"{text} dibuka, {detail}"))
        elif access.can_attempt is not None:
            detail = (
                "attempt dapat dimulai"
                if access.can_attempt
                else "attempt belum dapat dimulai"
            )
            lines.append(_line(True, f"{text} dibuka, {detail}"))
        else:
            lines.append(_line(True, f"{text} dibuka"))
    rejected = [item for item in report.not_enrolled.activities if not item.opened]
    if report.not_enrolled.activities:
        lines.append(
            _line(
                len(rejected) == len(report.not_enrolled.activities),
                f"{report.not_enrolled.username} (tidak terdaftar) ditolak pada {len(rejected)}/{len(report.not_enrolled.activities)} activity",
            )
        )
    return lines


def format_report(report: StudentAccessReport, *, enrolled_now: bool) -> str:
    visibility = report.visibility
    total = len(visibility.weekly_sections)
    seen = len(report.enrolled.weekly_sections)
    lines = [f"Verifikasi akses mahasiswa pada course {report.moodle_course_id}:"]
    lines.append(_line(visibility.course_visible, "Course terlihat oleh mahasiswa"))
    if visibility.hidden_sections:
        hidden = ", ".join(str(number) for number in visibility.hidden_sections)
        lines.append(
            _line(
                False,
                f"{total} section mingguan, tersembunyi: minggu {hidden} (pakai --show-hidden)",
            )
        )
    else:
        lines.append(
            _line(total > 0, f"{total} section mingguan, tidak ada yang tersembunyi")
        )
    enrolled_text = "didaftarkan" if enrolled_now else "sudah terdaftar"
    lines.append(
        _line(True, f"{report.enrolled.username} {enrolled_text} sebagai student")
    )
    if report.enrolled.can_open:
        lines.append(
            _line(
                report.enrolled_sees_all_sections,
                f"{report.enrolled.username} membuka course dan melihat {seen}/{total} section mingguan",
            )
        )
    else:
        lines.append(
            _line(
                False,
                f"{report.enrolled.username} ditolak Moodle ({report.enrolled.error_code})",
            )
        )
    lines.extend(_activity_lines(report))
    if report.not_enrolled_rejected:
        lines.append(
            _line(
                True,
                f"{report.not_enrolled.username} (tidak terdaftar) ditolak Moodle: {report.not_enrolled.error_code}",
            )
        )
    else:
        lines.append(
            _line(
                False,
                f"{report.not_enrolled.username} (tidak terdaftar) justru bisa membuka course",
            )
        )
    lines.append(
        "Hasil: student access TERBUKTI."
        if report.ok
        else "Hasil: student access BELUM terbukti."
    )
    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.verify_student_access",
        description="Daftarkan mahasiswa uji ke course hasil eksekusi dan buktikan student access.",
    )
    parser.add_argument(
        "--course-id", type=int, required=True, help="ID course Moodle target eksekusi."
    )
    parser.add_argument(
        "--show-hidden",
        action="store_true",
        help="Tampilkan course dan section mingguan yang tersembunyi sebelum diverifikasi.",
    )
    parser.add_argument(
        "--no-enrol",
        action="store_true",
        help="Jangan mendaftarkan mahasiswa; hanya verifikasi.",
    )
    parser.add_argument(
        "--start-quiz",
        action="store_true",
        help="Mulai lalu selesaikan satu attempt quiz sebagai mahasiswa terdaftar (hanya untuk course uji).",
    )
    return parser.parse_args(argv)


async def run(
    access: MoodleStudentAccessService,
    course_id: int,
    *,
    enrolled: tuple[str, str],
    not_enrolled: tuple[str, str],
    show_hidden: bool = False,
    enrol: bool = True,
    start_quiz: bool = False,
) -> tuple[StudentAccessReport, bool]:
    """Jalankan alur demo; mengembalikan laporan dan apakah mahasiswa baru didaftarkan."""
    enrolled_now = False
    if enrol:
        enrolled_now = not await access.is_enrolled(course_id, enrolled[0])
        await access.enrol_students(course_id, [enrolled[0]])
    if show_hidden:
        await access.ensure_visible(course_id)
    report = await access.verify(
        course_id, enrolled=enrolled, not_enrolled=not_enrolled, start_quiz=start_quiz
    )
    return report, enrolled_now


async def main(
    argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None
) -> int:
    args = parse_args(argv)
    try:
        enrolled, not_enrolled = student_credentials(os.environ if env is None else env)
    except StudentAccessSetupError as exc:
        print(f"Konfigurasi belum lengkap: {exc}", file=sys.stderr)
        return 2
    async with MoodleClient.from_settings(settings) as client:
        access = MoodleStudentAccessService.from_settings(
            MoodleIntegrationService(client), settings
        )
        try:
            report, enrolled_now = await run(
                access,
                args.course_id,
                enrolled=enrolled,
                not_enrolled=not_enrolled,
                show_hidden=args.show_hidden,
                enrol=not args.no_enrol,
                start_quiz=args.start_quiz,
            )
        except StudentAccessSetupError as exc:
            print(f"Belum siap: {exc}", file=sys.stderr)
            return 2
        except MoodleError as exc:
            print(
                f"Moodle menolak operasi ({exc.error_type}, {exc.code}): {exc.message}",
                file=sys.stderr,
            )
            return 1
    print(format_report(report, enrolled_now=enrolled_now))
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))