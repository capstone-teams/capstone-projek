"""Seed data contoh: RPS, course, course plan, minggu, konten, dan aktivitas.

Dipakai selama endpoint ``/courses`` belum ada (BE-14): tanpa route, data contoh
tidak bisa dibuat lewat API, sedangkan pengujian frontend/schema butuh isi nyata.
Script ini menulis langsung lewat ORM sehingga default dan aturan domain ikut
berlaku — termasuk ``file_hash`` yang wajib SHA-256 hex 64 karakter, aturan yang
membuat baris hasil ``INSERT`` mentah ditolak saat dibaca (422).

Idempotent: dijalankan dua kali tidak membuat duplikat. Pakai ``--reset`` untuk
menghapus data contoh lalu membuatnya ulang.

Pemakaian (dari folder ``backend/``, server lokal atau dalam container)::

    uv run python -m scripts.seed_sample_course
    uv run python -m scripts.seed_sample_course --reset

Prasyarat: database terjangkau, migrasi sudah diterapkan, dan akun uji ada
(``uv run python -m scripts.seed_test_accounts``).
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.database import dispose_engine, get_session_factory
from src.models import (
    Activity,
    ActivityStatus,
    ActivityType,
    AgentRun,
    AgentRunStatus,
    AgentRunType,
    Category,
    Content,
    ContentStatus,
    ContentType,
    Course,
    CoursePlan,
    CoursePlanStatus,
    CoursePlanWeek,
    CourseStatus,
    RPS,
    RPSAnalysis,
    RPSStatus,
    User,
)

__all__ = ["main", "seed_sample_course"]

COURSE_CODE = "IF2230"
COURSE_NAME = "Basis Data"
CATEGORY_NAME = "Teknik Informatika"
RPS_FILE = "contoh-rps-basis-data.pdf"
RPS_HASH = hashlib.sha256(b"contoh-course-plan-if2230-v1").hexdigest()
SHORTNAME = "IF2230-SAMPLE"

#: (minggu, topik, sub-CPMK, metode, assessment). UTS/UAS punya topik kosong.
WEEKS: list[tuple[int, str, list[str], list[str], dict[str, Any] | None]] = [
    (
        1, "Konsep dasar basis data relasional", ["SUB-1"], ["Kuliah/ceramah", "Diskusi"],
        {"type": "kuis", "description": "Ketepatan menjelaskan model relasional", "weight_percent": 5},
    ),
    (2, "Entity Relationship Diagram", ["SUB-1"], ["Latihan terbimbing"], None),
    (
        3, "Normalisasi hingga 3NF", ["SUB-2"], ["Latihan soal"],
        {"type": "kuis", "description": "Ketepatan normalisasi 3NF", "weight_percent": 5},
    ),
    (4, "Query SQL dan JOIN", ["SUB-3"], ["Praktikum"], None),
    (5, "Agregasi, Subquery, dan View", ["SUB-3"], ["Praktikum"], None),
    (6, "Transaksi dan Integritas Data", ["SUB-4"], ["Kuliah/ceramah"], None),
    (7, "Perancangan Basis Data Studi Kasus", ["SUB-4"], ["Diskusi"], None),
    (8, "Ujian Tengah Semester", [], [], None),
    (9, "Pengantar Sistem Basis Data Terdistribusi", ["SUB-5"], ["Kuliah/ceramah"], None),
    (10, "Indeks dan Optimasi Query", ["SUB-5"], ["Praktikum"], None),
    (11, "NoSQL dan Basis Data Dokumen", ["SUB-6"], ["Diskusi"], None),
    (12, "Keamanan dan Hak Akses Basis Data", ["SUB-6"], ["Kuliah/ceramah"], None),
    (13, "Backup, Restore, dan Pemulihan Bencana", ["SUB-7"], ["Latihan terbimbing"], None),
    (14, "Basis Data untuk Aplikasi Web", ["SUB-7"], ["Praktikum"], None),
    (
        15, "Proyek Akhir Perancangan Basis Data", ["SUB-7"], ["Praktikum"],
        {"type": "tugas", "description": "Kualitas rancangan proyek akhir", "weight_percent": 20},
    ),
    (16, "Ujian Akhir Semester", [], [], None),
]

EXAM_WEEKS = {8, 16}
ASSESSED_WEEKS = {1, 3, 15}


def _is_exam(week: int) -> bool:
    return week in EXAM_WEEKS


def _learning_markdown(topic: str) -> str:
    return (
        f"# {topic}\n\n"
        "## Tujuan Pembelajaran\n- Menjelaskan konsep inti.\n- Menerapkan konsep pada studi kasus.\n\n"
        f"## Konsep Inti\n{topic} dibahas dari definisi hingga penerapannya pada basis data relasional.\n\n"
        "## Contoh Penerapan\nDiterapkan pada studi kasus perpustakaan kampus.\n\n"
        "## Kesalahan Umum\nMengabaikan integritas data dan tidak memeriksa rencana eksekusi query.\n\n"
        "## Referensi\n- Database System Concepts (Silberschatz) — silabus.\n"
    )


def _learning_content(topic: str) -> dict[str, Any]:
    return {
        "type": "learning_material",
        "title": topic,
        "summary": f"Materi {topic.lower()} untuk satu pertemuan.",
        "learning_objectives": [f"Menjelaskan {topic.lower()}", "Menerapkan konsep pada studi kasus"],
        "sections": [
            {"order": 1, "title": "Konsep inti", "content": f"{topic} dibahas dari definisi hingga penerapannya."},
            {"order": 2, "title": "Contoh penerapan", "content": "Studi kasus perpustakaan kampus."},
            {"order": 3, "title": "Kesalahan umum", "content": "Mengabaikan integritas data."},
        ],
        "examples": [{"title": "Perpustakaan kampus", "description": "Data buku, anggota, dan peminjaman."}],
        "references": [{"title": "Database System Concepts (Silberschatz)", "url": None}],
    }


def _resource_content(topic: str) -> dict[str, Any]:
    return {
        "type": "resource",
        "title": f"Referensi tambahan: {topic}",
        "description": "Bacaan pendukung untuk materi minggu ini.",
        "resource_type": "external_link",
        "url": None,
    }


ASSIGNMENT = {
    "type": "assignment",
    "title": "Latihan Query JOIN",
    "description": "Menggabungkan dua tabel pada studi kasus perpustakaan.",
    "instructions": ["Tulis 3 query JOIN dan jelaskan hasilnya."],
    "submission_type": ["file"],
    "due": None,
    "grading": {"max_grade": 100, "rubric": []},
}

QUIZ = {
    "type": "quiz",
    "title": "Kuis Normalisasi",
    "description": "Memeriksa pemahaman normalisasi hingga 3NF.",
    "questions": [
        {
            "type": "multiple_choice",
            "question": "Bentuk normal yang menghilangkan ketergantungan transitif adalah?",
            "options": [
                {"text": "3NF", "correct": True},
                {"text": "1NF", "correct": False},
                {"text": "2NF", "correct": False},
            ],
            "explanation": "3NF menghilangkan ketergantungan transitif pada atribut non-kunci.",
        }
    ],
}


async def _reset(session: AsyncSession) -> None:
    """Hapus data contoh (dan hanya data contoh) dalam urutan FK."""
    course = (
        await session.execute(select(Course).where(Course.shortname == SHORTNAME))
    ).scalar_one_or_none()
    if course is not None:
        plan_ids = (
            await session.execute(select(CoursePlan.id).where(CoursePlan.course_id == course.id))
        ).scalars().all()
        week_ids = (
            await session.execute(
                select(CoursePlanWeek.id).where(CoursePlanWeek.course_plan_id.in_(plan_ids))
            )
        ).scalars().all()
        await session.execute(delete(Content).where(Content.course_plan_week_id.in_(week_ids)))
        await session.execute(delete(Activity).where(Activity.course_plan_week_id.in_(week_ids)))
        await session.execute(delete(CoursePlanWeek).where(CoursePlanWeek.id.in_(week_ids)))
        await session.execute(delete(CoursePlan).where(CoursePlan.id.in_(plan_ids)))
        await session.execute(delete(AgentRun).where(AgentRun.course_id == course.id))
        rps_id = course.rps_id
        await session.execute(delete(Course).where(Course.id == course.id))
        await session.execute(delete(RPSAnalysis).where(RPSAnalysis.rps_id == rps_id))
        await session.execute(delete(RPS).where(RPS.id == rps_id))
        print("reset: data contoh lama dihapus")
    await session.commit()


async def seed_sample_course(session: AsyncSession, *, username: str = "dosen.demo") -> dict[str, Any]:
    user = (
        await session.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if user is None:
        raise SystemExit(
            f"Akun '{username}' tidak ada. Jalankan scripts.seed_test_accounts lebih dulu."
        )

    category = (
        await session.execute(select(Category).where(Category.name == CATEGORY_NAME))
    ).scalar_one_or_none()
    if category is None:
        category = Category(name=CATEGORY_NAME, description="Contoh kategori", sort_order=0)
        session.add(category)
        await session.flush()

    rps = (
        await session.execute(select(RPS).where(RPS.file_hash == RPS_HASH))
    ).scalar_one_or_none()
    if rps is None:
        rps = RPS(
            owner_id=user.id,
            file_name=RPS_FILE,
            file_type="application/pdf",
            file_path=f"storage/rps/{RPS_FILE}",
            file_hash=RPS_HASH,
            schema_version="2.0",
            status=RPSStatus.ANALYZED,
            analyzed_at=datetime.now(UTC),
            structured_data={
                "schema_version": "2.0",
                "course": {"name": COURSE_NAME, "code": COURSE_CODE, "credits": 3, "semester": 3},
                "weeks": [
                    {
                        "week": week,
                        "week_type": "uts" if week == 8 else "uas" if week == 16 else "regular",
                        "topics": [] if _is_exam(week) else [topic],
                        "cpmk": [] if _is_exam(week) else [f"CPMK-{(week - 1) // 3 + 1}"],
                        "sub_cpmk": [] if _is_exam(week) else sub,
                        "teaching_method": method,
                        "media": [] if _is_exam(week) else ["LMS"],
                        "assessment": assessment,
                    }
                    for week, topic, sub, method, assessment in WEEKS
                ],
                "extraction": {"extractor": "seed_sample_course", "confidence": 1.0},
            },
        )
        session.add(rps)
        await session.flush()

    analysis = (
        await session.execute(select(RPSAnalysis).where(RPSAnalysis.rps_id == rps.id))
    ).scalars().first()
    if analysis is None:
        analysis = RPSAnalysis(
            rps_id=rps.id,
            version=1,
            course_identity={"name": COURSE_NAME, "code": COURSE_CODE},
            weekly_distribution=rps.structured_data["weeks"],
            raw_analysis=rps.structured_data,
        )
        session.add(analysis)
        await session.flush()

    course = (
        await session.execute(select(Course).where(Course.shortname == SHORTNAME))
    ).scalar_one_or_none()
    if course is None:
        course = Course(
            instructor_id=user.id,
            rps_id=rps.id,
            category=category.id,
            course_format="topics",
            sortorder=1,
            fullname=f"{COURSE_NAME} (Contoh)",
            shortname=SHORTNAME,
            description="Course contoh untuk menguji generator course plan dan konten.",
            semester="3",
            status=CourseStatus.DRAFT,
        )
        session.add(course)
        await session.flush()

    # Hanya run GENERATION yang masih dirujuk: content_plans tidak lagi menyimpan
    # agent run (kolom itu dihapus pada BE-14.1), sedangkan contents masih.
    generation_run = (
        await session.execute(
            select(AgentRun).where(
                AgentRun.course_id == course.id,
                AgentRun.run_type == AgentRunType.GENERATION,
            )
        )
    ).scalars().first()
    if generation_run is None:
        generation_run = AgentRun(
            course_id=course.id,
            run_type=AgentRunType.GENERATION,
            status=AgentRunStatus.COMPLETED,
            current_stage="done",
            model_name="seed-sample",
            model_runtime="local",
            input_context={"source": "seed_sample_course"},
            output_reference={"seeded": True},
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(generation_run)
        await session.flush()

    plan = (
        await session.execute(
            select(CoursePlan).where(CoursePlan.course_id == course.id, CoursePlan.version == 1)
        )
    ).scalar_one_or_none()
    if plan is None:
        plan = CoursePlan(
            course_id=course.id,
            rps_analysis_id=analysis.id,
            version=1,
            status=CoursePlanStatus.PENDING_REVIEW,
            plan_data={
                "course": {"name": COURSE_NAME, "code": COURSE_CODE, "weeks": 16},
                "weeks": [
                    {
                        "week_number": week,
                        "title": topic,
                        "learning_outcomes": sub,
                        "topics": [] if _is_exam(week) else [topic],
                        "teaching_methods": method,
                        "assessment": assessment,
                    }
                    for week, topic, sub, method, assessment in WEEKS
                ],
            },
        )
        session.add(plan)
        await session.flush()

    stats = {"weeks": 0, "materials": 0, "resources": 0, "activities": 0}
    for week, topic, sub, method, assessment in WEEKS:
        plan_week = (
            await session.execute(
                select(CoursePlanWeek).where(
                    CoursePlanWeek.course_plan_id == plan.id, CoursePlanWeek.week_number == week
                )
            )
        ).scalar_one_or_none()
        if plan_week is None:
            plan_week = CoursePlanWeek(
                course_plan_id=plan.id,
                week_number=week,
                title=topic,
                learning_outcomes=sub,
                topics=[] if _is_exam(week) else [topic],
                methods=method,
                assessment=assessment,
                metadata_={"week_type": "exam" if _is_exam(week) else "regular"},
            )
            session.add(plan_week)
            await session.flush()
            stats["weeks"] += 1

        if _is_exam(week):
            continue

        material = (
            await session.execute(
                select(Content).where(
                    Content.course_plan_week_id == plan_week.id,
                    Content.content_type == ContentType.LEARNING_MATERIAL,
                )
            )
        ).scalars().first()
        if material is None:
            session.add(
                Content(
                    course_plan_week_id=plan_week.id,
                    title=topic,
                    content_type=ContentType.LEARNING_MATERIAL,
                    content_data=_learning_content(topic),
                    content_markdown=_learning_markdown(topic),
                    version=1,
                    status=ContentStatus.VALIDATED,
                    generated_by_agent_run_id=generation_run.id,
                )
            )
            stats["materials"] += 1

        if week in (1, 4):
            resource = (
                await session.execute(
                    select(Content).where(
                        Content.course_plan_week_id == plan_week.id,
                        Content.content_type == ContentType.RESOURCE,
                    )
                )
            ).scalars().first()
            if resource is None:
                session.add(
                    Content(
                        course_plan_week_id=plan_week.id,
                        title=f"Referensi tambahan: {topic}",
                        content_type=ContentType.RESOURCE,
                        content_data=_resource_content(topic),
                        version=1,
                        status=ContentStatus.VALIDATED,
                        generated_by_agent_run_id=generation_run.id,
                    )
                )
                stats["resources"] += 1

        for activity_type, payload in (
            (ActivityType.ASSIGNMENT, ASSIGNMENT if week == 4 else None),
            (ActivityType.QUIZ, QUIZ if week == 3 else None),
        ):
            if payload is None:
                continue
            existing = (
                await session.execute(
                    select(Activity).where(
                        Activity.course_plan_week_id == plan_week.id,
                        Activity.type == activity_type,
                    )
                )
            ).scalars().first()
            if existing is None:
                session.add(
                    Activity(
                        course_plan_week_id=plan_week.id,
                        type=activity_type,
                        title=payload["title"],
                        activity_data=payload,
                        enabled=True,
                        version=1,
                        status=ActivityStatus.VALIDATED,
                    )
                )
                stats["activities"] += 1

    await session.commit()
    return {
        "user": username,
        "rps_id": rps.id,
        "rps_analysis_id": analysis.id,
        "course_id": course.id,
        "course_plan_id": plan.id,
        **stats,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default="dosen.demo", help="Pemilik data contoh.")
    parser.add_argument("--reset", action="store_true", help="Hapus data contoh lalu buat ulang.")
    args = parser.parse_args()

    async with get_session_factory()() as session:
        if args.reset:
            await _reset(session)
        summary = await seed_sample_course(session, username=args.username)

    print("Seed course contoh selesai:")
    for key, value in summary.items():
        print(f"  {key:16} {value}")
    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
