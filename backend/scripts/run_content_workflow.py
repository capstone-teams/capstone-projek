import asyncio
import sys
import traceback
from pathlib import Path

# Agar bisa dijalankan dari folder mana pun: naik sampai ketemu folder yang berisi src/.
_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "src").is_dir())
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.config.database import get_session_factory, dispose_engine
from src.services.content.generate_service import generate_contents, list_weeks
from src.services.content.review_service import (
    ActivityReviewService,
    ContentReviewService,
)

DEFAULT_ADDITIONAL_PROMPT = "Jelaskan materi dengan contoh praktis."


def _v(value):
    """Nilai string dari enum (atau string biasa)."""
    return getattr(value, "value", value)


def ask_yes_no(question: str, default: bool) -> bool:
    hint = "Y/n" if default else "y/N"
    answer = input(f"{question} [{hint}]: ").strip().lower()

    if not answer:
        return default

    return answer in ("y", "ya", "yes")


async def print_event(event_type, message, **fields):
    week = fields.pop("week", "-")
    attempt = fields.pop("attempt", None)
    content_type = fields.pop("content_type", None)

    prefix = f"[Minggu {week}]"
    if content_type:
        prefix += f"[{content_type}]"
    if attempt is not None:
        prefix += f"[Percobaan {attempt}]"

    extras = []

    if fields.get("tokens_input") is not None:
        extras.append(f"in={fields['tokens_input']}")
    if fields.get("tokens_output") is not None:
        extras.append(f"out={fields['tokens_output']}")
    if fields.get("duration_ms") is not None:
        extras.append(f"{fields['duration_ms']}ms")
    if fields.get("reason_code"):
        extras.append(f"reason={fields['reason_code']}")

    line = f"{prefix} {message}"

    if extras:
        line += f" ({', '.join(extras)})"

    print(line, flush=True)

    for detail in fields.get("details") or []:
        print(f"      - {detail}", flush=True)


async def print_trace(**fields):
    print(
        f"    TRACE attempt={fields.get('attempt')} "
        f"validation={fields.get('validation')} "
        f"model={fields.get('model')} "
        f"{fields.get('duration_ms')}ms",
        flush=True,
    )


def print_menu():
    print("\n=== CONTENT WORKFLOW ===")
    print("1. Generate content (JSON / Pydantic output)")
    print("2. Review content   (Learning Material / Resource)")
    print("3. Review activity  (Assignment / Quiz)")
    print("0. Exit")


CONTENT_TYPE_CHOICES = {
    "1": "LEARNING_MATERIAL",
    "2": "RESOURCE",
    "3": "QUIZ",
    "4": "ASSIGNMENT",
}


async def print_weeks(db, course_plan_id) -> bool:
    """Tampilkan tipe tiap minggu dari course plan."""
    try:
        weeks = await list_weeks(db, course_plan_id)
    except Exception as exc:
        print(f"Gagal membaca minggu: {exc}")
        return False

    print("\nMinggu pada course plan ini:")
    print(f"{'Minggu':<8}{'Tipe':<12}{'Topics':<8}{'Sub-CPMK':<10}Judul")

    for w in weeks:
        d = w.week_data
        outcomes = "ada" if d.learning_outcomes else "kosong"

        print(
            f"{w.week_number:<8}"
            f"{d.week_type:<12}"
            f"{len(d.topics):<8}"
            f"{outcomes:<10}"
            f"{d.title or '-'}"
        )

    print()
    return True


async def run_generation(db):
    course_plan_id = input("Course Plan ID: ").strip()

    if not course_plan_id:
        print("Course Plan ID tidak boleh kosong.")
        return

    if not await print_weeks(db, course_plan_id):
        return

    week_input = input(
        "Week numbers (Enter = all weeks, contoh: 1 atau 1,3): "
    ).strip()

    if week_input:
        try:
            week_numbers = [
                int(week.strip())
                for week in week_input.split(",")
            ]
        except ValueError:
            print("Format minggu tidak valid.")
            return
    else:
        week_numbers = None

    print("Jenis konten: Enter = otomatis sesuai tipe minggu")
    print(
        "  1 = materi, 2 = resource, 3 = kuis, "
        "4 = tugas (boleh lebih dari satu, contoh 1,4)"
    )

    type_input = input("Pilih jenis konten: ").strip()

    if type_input:
        try:
            content_types = [
                CONTENT_TYPE_CHOICES[choice.strip()]
                for choice in type_input.split(",")
            ]
        except KeyError:
            print("Pilihan jenis konten tidak valid.")
            return
    else:
        content_types = None

    additional_prompt = input(
        f"Additional prompt (Enter = \"{DEFAULT_ADDITIONAL_PROMPT}\"): "
    ).strip() or DEFAULT_ADDITIONAL_PROMPT

    if content_types is None:
        include_assignment = ask_yes_no(
            "Tambahkan assignment di minggu reguler?", default=False
        )
        include_resources = ask_yes_no(
            "Buat learning resource dulu sebagai bahan materi?",
            default=True,
        )
    else:
        include_assignment = False
        include_resources = True

    try:
        results = await generate_contents(
            db=db,
            course_plan_id=course_plan_id,
            week_numbers=week_numbers,
            content_types=content_types,
            additional_prompt=additional_prompt,
            include_assignment=include_assignment,
            include_resources=include_resources,
            emit_event=print_event,
            record_trace=print_trace,
        )

    except ValueError as exc:
        print(f"\nGENERATION FAILED: {exc}")
        return

    except Exception as exc:
        print(f"\nGENERATION FAILED: {exc}")
        traceback.print_exc()
        return

    successful = 0
    failed = 0

    print("\n=== GENERATION RESULTS ===")

    for result in results:
        print(f"\n{'=' * 60}")
        print(
            f"WEEK {result.ctx.week_number} - "
            f"{result.content_type}"
        )
        print("=" * 60)

        if result.error is not None:
            failed += 1

            print(f"GENERATION FAILED: {result.error}")

            if getattr(result.error, "reason_code", None):
                print(f"Reason     : {result.error.reason_code}")

            for detail in getattr(result.error, "details", []):
                print(f"      - {detail}")

            continue

        if result.material is None:
            failed += 1
            print("Tidak ada output Pydantic.")
            continue

        successful += 1

        # Hanya menampilkan hasil Pydantic.
        # Tidak melakukan insert/update database.
        print(result.material.model_dump_json(indent=2))

    print("\n=== GENERATION SUMMARY ===")
    print(f"Total items : {len(results)}")
    print(f"Successful  : {successful}")
    print(f"Failed      : {failed}")
    print("Database    : Tidak ada hasil generation yang disimpan.")


async def run_review(db):
    """Review Learning Material / Resource (tabel contents)."""
    service = ContentReviewService()

    content_id = input("\nContent ID: ").strip()

    if not content_id:
        print("Content ID tidak boleh kosong.")
        return

    while True:
        print("\n=== CONTENT REVIEW ===")
        print("1. Validate content")
        print("2. Retry content")
        print("3. Submit for review")
        print("4. Approve content")
        print("5. Reject content")
        print("0. Back")

        choice = input("Pilih aksi: ").strip()

        try:
            if choice == "1":
                content = await service.validate_content(
                    db=db,
                    content_id=content_id,
                )

            elif choice == "2":
                revision_notes = input("Catatan revisi dosen: ").strip()
                additional_prompt = input(
                    "Instruksi gaya penyampaian (opsional): "
                ).strip()

                content = await service.retry_content(
                    db=db,
                    content_id=content_id,
                    additional_prompt=additional_prompt,
                    revision_notes=revision_notes,
                    emit_event=print_event,
                    record_trace=print_trace,
                )

            elif choice == "3":
                content = await service.submit_for_review(
                    db=db,
                    content_id=content_id,
                )

            elif choice == "4":
                content = await service.approve_content(
                    db=db,
                    content_id=content_id,
                )

            elif choice == "5":
                reason = input("Alasan penolakan: ").strip()

                content = await service.reject_content(
                    db=db,
                    content_id=content_id,
                    reason=reason,
                )

            elif choice == "0":
                break

            else:
                print("Pilihan tidak valid.")
                continue

            print("\n=== REVIEW RESULT ===")
            print(f"Content ID : {content.id}")
            print(f"Type       : {_v(content.content_type)}")
            print(f"Title      : {content.title}")
            print(f"Version    : {content.version}")
            print(f"Status     : {_v(content.status)}")

        except Exception as exc:
            await db.rollback()
            print(f"\nOPERATION FAILED: {exc}")
            traceback.print_exc()


async def run_activity_review(db):
    """Review Assignment / Quiz (tabel activities)."""
    service = ActivityReviewService()

    activity_id = input("\nActivity ID: ").strip()

    if not activity_id:
        print("Activity ID tidak boleh kosong.")
        return

    while True:
        print("\n=== ACTIVITY REVIEW ===")
        print("1. Validate activity")
        print("2. Retry activity")
        print("3. Approve activity")
        print("4. Mark executed (setelah dieksekusi ke Moodle)")
        print("0. Back")

        choice = input("Pilih aksi: ").strip()

        try:
            if choice == "1":
                activity = await service.validate_activity(
                    db=db,
                    activity_id=activity_id,
                )

            elif choice == "2":
                revision_notes = input("Catatan revisi dosen: ").strip()
                additional_prompt = input(
                    "Instruksi gaya penyampaian (opsional): "
                ).strip()

                activity = await service.retry_activity(
                    db=db,
                    activity_id=activity_id,
                    additional_prompt=additional_prompt,
                    revision_notes=revision_notes,
                    emit_event=print_event,
                    record_trace=print_trace,
                )

            elif choice == "3":
                activity = await service.approve_activity(
                    db=db,
                    activity_id=activity_id,
                )

            elif choice == "4":
                activity = await service.mark_executed(
                    db=db,
                    activity_id=activity_id,
                )

            elif choice == "0":
                break

            else:
                print("Pilihan tidak valid.")
                continue

            print("\n=== REVIEW RESULT ===")
            print(f"Activity ID: {activity.id}")
            print(f"Type       : {_v(activity.type)}")
            print(f"Title      : {activity.title}")
            print(f"Version    : {activity.version}")
            print(f"Status     : {_v(activity.status)}")

        except Exception as exc:
            await db.rollback()
            print(f"\nOPERATION FAILED: {exc}")
            traceback.print_exc()


async def main():
    session_factory = get_session_factory()

    try:
        async with session_factory() as db:
            while True:
                print_menu()
                choice = input("Pilih menu: ").strip()

                if choice == "1":
                    await run_generation(db)

                elif choice == "2":
                    await run_review(db)

                elif choice == "3":
                    await run_activity_review(db)

                elif choice == "0":
                    break

                else:
                    print("Pilihan tidak valid.")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
