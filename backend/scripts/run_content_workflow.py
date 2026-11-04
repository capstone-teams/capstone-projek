
import asyncio

from src.config.database import get_session_factory, dispose_engine
from src.services.content.generate_service import generate_contents
from src.services.content.review_service import ContentReviewService
from src.services.content.repository import ContentGenerationRepository


async def print_event(event_type, message, **fields):
    week = fields.pop("week", "-")
    attempt = fields.pop("attempt", None)

    prefix = f"[Minggu {week}]"
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
    print("1. Generate content")
    print("2. Review content")
    print("0. Exit")


async def run_generation(db):
    course_plan_id = input("Course Plan ID: ").strip()

    if not course_plan_id:
        print("Course Plan ID tidak boleh kosong.")
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

    try:
        results = await generate_contents(
            db=db,
            course_plan_id=course_plan_id,
            week_numbers=week_numbers,
            additional_prompt="Jelaskan materi dengan contoh praktis.",
            emit_event=print_event,
            record_trace=print_trace,
        )
    except ValueError as exc:
        print(f"\nGENERATION FAILED: {exc}")
        return
    except Exception as exc:
        await db.rollback()
        print(f"\nGENERATION FAILED: {exc}")
        return

    content_ids = []

    for result in results:
        print(f"\n{'=' * 60}")
        print(f"WEEK {result.ctx.week}")
        print("=" * 60)

        if result.error:
            print(f"GENERATION FAILED: {result.error}")
            continue

        print(result.material.model_dump_json(indent=2))

        content = await ContentGenerationRepository.get_by_week_id(
            db,
            result.ctx.course_plan_week_id,
        )

        if content is not None:
            content_ids.append(
                (result.ctx.week, content.id)
            )
            print(f"Content ID : {content.id}")
        else:
            print("Content ID : Tidak ditemukan di database.")

    successful = sum(1 for r in results if r.material is not None and r.error is None)
    failed = sum(1 for r in results if r.error is not None)

    print("\n=== GENERATION SUMMARY ===")
    print(f"Total weeks : {len(results)}")
    print(f"Successful  : {successful}")
    print(f"Failed      : {failed}")

    print("\n=== CONTENT IDS ===")
    for week, content_id in content_ids:
        print(f"Minggu {week}: {content_id}")


async def run_review(db):
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
                additional_prompt = input("Instruksi revisi: ").strip()

                content = await service.retry_content(
                    db=db,
                    content_id=content_id,
                    additional_prompt=additional_prompt,
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
            print(f"Version    : {content.version}")
            print(f"Status     : {content.status.value}")

        except Exception as exc:
            await db.rollback()
            print(f"\nOPERATION FAILED: {exc}")


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

                elif choice == "0":
                    break

                else:
                    print("Pilihan tidak valid.")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
