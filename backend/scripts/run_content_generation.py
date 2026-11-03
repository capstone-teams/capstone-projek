import asyncio

from src.config.database import get_session_factory, dispose_engine
from src.services.content.service import generate_contents


async def print_event(event_type, message, **fields):
    """Cetak setiap tahap proses saat terjadi."""
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
    """Cetak ringkasan tiap percobaan (opsional)."""
    print(
        f"    TRACE attempt={fields.get('attempt')} "
        f"validation={fields.get('validation')} "
        f"model={fields.get('model')} "
        f"{fields.get('duration_ms')}ms",
        flush=True,
    )


async def main():
    rps_id = input("RPS ID: ").strip()

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
            print("Format minggu tidak valid. Contoh: 1,3")
            return
    else:
        week_numbers = None

    session_factory = get_session_factory()

    try:
        async with session_factory() as db:
            results = await generate_contents(
                db=db,
                rps_id=rps_id,
                week_numbers=week_numbers,
                additional_prompt="Jelaskan materi dengan contoh praktis.",
                emit_event=print_event,
                record_trace=print_trace,  # hapus kalau tidak perlu
            )

        for result in results:
            print(f"\n{'=' * 60}")
            print(f"WEEK {result.ctx.week}")
            print("=" * 60)

            if result.error:
                print(f"GENERATION FAILED: {result.error}")
                continue

            print(result.material.model_dump_json(indent=2))

        successful = sum(1 for r in results if r.material is not None)
        failed = sum(1 for r in results if r.error is not None)

        print("\n=== GENERATION SUMMARY ===")
        print(f"Total weeks : {len(results)}")
        print(f"Successful  : {successful}")
        print(f"Failed      : {failed}")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
