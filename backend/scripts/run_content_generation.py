import asyncio

from src.config.database import get_session_factory, dispose_engine
from src.services.content.service import generate_contents


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
            )

        for result in results:
            print(f"\n{'=' * 60}")
            print(f"WEEK {result.ctx.week}")
            print("=" * 60)

            if result.error:
                print(f"GENERATION FAILED: {result.error}")
                continue

            print(result.material.model_dump_json(indent=2))

        successful = sum(
            1 for result in results
            if result.material is not None
        )

        failed = sum(
            1 for result in results
            if result.error is not None
        )

        print("\n=== GENERATION SUMMARY ===")
        print(f"Total weeks : {len(results)}")
        print(f"Successful  : {successful}")
        print(f"Failed      : {failed}")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
