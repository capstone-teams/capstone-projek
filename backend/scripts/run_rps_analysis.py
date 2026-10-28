"""CLI interaktif untuk menguji RPS Analysis Service (BE-09.2).

Memanggil `analyze_rps()` langsung, sehingga yang diuji adalah jalur yang sama
dengan yang akan dipakai orchestrator: parse YAML, panggil LLM, validasi,
retry dengan feedback, event progres, dan trace per percobaan.
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Memastikan root backend tersedia di sys.path.
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.services.analysis.service import (  # sesuaikan path modul service
    RPSAnalysisError,
    analyze_rps,
)
from src.services.llm import OpenAIProvider

EVENT_PREFIX_WIDTH = 31  # lebar "[  0.00s] EVENT_TYPE          "


# --------------------------------------------------------------------------
# Input
# --------------------------------------------------------------------------


def read_yaml_file(label: str) -> str:
    """Membaca isi file YAML berdasarkan path yang dimasukkan pengguna."""
    while True:
        path_input = input(f"Path file {label}: ").strip()

        if not path_input:
            print("[PERINGATAN] Path tidak boleh kosong.")
            continue

        path = Path(path_input).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

        if not path.is_file():
            print(f"[GAGAL] File tidak ditemukan: {path}")
            continue

        try:
            content = path.read_text(encoding="utf-8")

            if not content.strip():
                print("[PERINGATAN] File kosong.")
                continue

            return content
        except OSError as exc:
            print(f"[GAGAL] Tidak bisa membaca file: {exc}")


def ask_yes_no(question: str) -> bool:
    """Meminta jawaban ya atau tidak."""
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()

        if answer in ("y", "ya", "yes"):
            return True
        if answer in ("n", "tidak", "no"):
            return False

        print("Masukkan y atau n.")


def read_optional_int(question: str) -> int | None:
    """Meminta angka opsional; Enter berarti memakai nilai dari konfigurasi."""
    while True:
        value = input(f"{question} (Enter = konfigurasi): ").strip()
        if not value:
            return None
        try:
            number = int(value)
        except ValueError:
            print("[PERINGATAN] Masukkan angka bulat.")
            continue
        if number < 0:
            print("[PERINGATAN] Tidak boleh negatif.")
            continue
        return number


def read_task_instruction() -> str:
    """Membaca instruksi dari file Markdown atau teks manual."""
    while True:
        value = input("Instruksi tugas / path file: ").strip()

        if value.lower() == "skip":
            return ""

        if not value:
            print("Masukkan instruksi, path file, atau ketik 'skip'.")
            continue

        path = Path(value).expanduser()

        # Jika input berupa path file Markdown, baca isi filenya.
        if path.suffix.lower() == ".md":
            if not path.is_absolute():
                path = Path.cwd() / path

            if not path.is_file():
                print(f"[GAGAL] File instruksi tidak ditemukan: {path}")
                continue

            try:
                content = path.read_text(encoding="utf-8")

                if not content.strip():
                    print("[PERINGATAN] File instruksi kosong.")
                    continue

                print(f"[SUKSES] File instruksi dibaca: {path}")
                return content
            except OSError as exc:
                print(f"[GAGAL] Tidak bisa membaca file: {exc}")
                continue

        # Selain path Markdown, input dianggap sebagai teks manual.
        return value


# --------------------------------------------------------------------------
# Pelaporan proses
# --------------------------------------------------------------------------


def make_reporters():
    """Buat callback event/trace yang mencetak proses secara langsung.

    Keduanya sama dengan yang nantinya diberikan orchestrator (BE-11):
    `emit_event` menerima event progres, `record_trace` menerima jejak
    tiap percobaan.
    """
    started = time.perf_counter()
    traces: list[dict] = []
    indent = " " * EVENT_PREFIX_WIDTH

    async def emit_event(*, event_type: str, message: str, **data) -> None:
        elapsed = time.perf_counter() - started
        print(f"[{elapsed:6.2f}s] {event_type:<20} {message}")

        if event_type == "LLM_RESPONDED":
            print(
                f"{indent}token: {data.get('tokens_input')} masuk, "
                f"{data.get('tokens_output')} keluar"
            )

        if data.get("reason_code") and event_type in ("RETRY_FIX", "ANALYSIS_FAILED"):
            print(f"{indent}alasan: {data['reason_code']}")

        for detail in data.get("details") or []:
            print(f"{indent}- {detail}")

    async def record_trace(**fields) -> None:
        traces.append(fields)

    return emit_event, record_trace, traces


def print_traces(traces: list[dict]) -> None:
    """Ringkasan jejak per percobaan."""
    if not traces:
        return

    print("\n" + "-" * 70)
    print("JEJAK PERCOBAAN")
    print("-" * 70)
    total_in = total_out = 0
    total_ms = 0.0

    for t in traces:
        print(
            f"#{t['attempt']} {t['prompt']} | model={t['model']} | "
            f"token={t['tokens_input']}/{t['tokens_output']} | "
            f"durasi={t['duration_ms']:.0f} ms | hasil={t['validation']}"
            + (f" ({t['reason_code']})" if t.get("reason_code") else "")
        )
        total_in += t["tokens_input"] or 0
        total_out += t["tokens_output"] or 0
        total_ms += t["duration_ms"] or 0

    print("-" * 70)
    print(f"Total token   : {total_in} masuk, {total_out} keluar ({total_in + total_out})")
    print(f"Total durasi  : {total_ms:.2f} ms")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------


async def main() -> int:
    # Proses sudah ditampilkan lewat event; log WARNING service memuat detail
    # error mentah dan akan mengacaukan tampilan CLI.
    logging.getLogger("src.services.analysis.rps_analysis").setLevel(logging.ERROR)

    print("=" * 70)
    print("CLI: MOODLE AGENTIC AI - RPS ANALYSIS (via analyze_rps)")
    print("=" * 70)

    provider = OpenAIProvider()

    if not provider.is_configured():
        print("[GAGAL] OPENAI_API_KEY belum dikonfigurasi di backend/.env.")
        return 1

    print(f"Provider : {provider.provider_name} ({provider.label})")
    print(f"Model    : {provider.model}")
    print("=" * 70)

    # 1. Input RPS.
    print("\n[1] INPUT DATA RPS")
    rps_yaml = read_yaml_file("RPS (YAML)")

    # 2. Instruksi tambahan (diteruskan sebagai additional_prompt).
    print("\n[2] INSTRUKSI TAMBAHAN")
    print(
        "Hanya untuk cara memfilter/memetakan data RPS. Masukkan path file .md, "
        "teks manual, atau ketik 'skip'."
    )
    if ask_yes_no("Tambahkan instruksi?"):
        additional_prompt = read_task_instruction()
    else:
        additional_prompt = ""

    # 3. Batas retry.
    print("\n[3] BATAS RETRY")
    max_fix_attempts = read_optional_int("Retry tambahan jika output tidak valid")

    # 4. Konfirmasi.
    print("\n" + "=" * 70)
    print("KONFIRMASI INPUT")
    print("=" * 70)
    print("RPS YAML         : berhasil dibaca")
    print(f"Instruksi        : {'Ya' if additional_prompt else 'Tidak'}")
    print(
        "Batas retry      : "
        f"{max_fix_attempts if max_fix_attempts is not None else 'dari konfigurasi'}"
    )

    if not ask_yes_no("Jalankan RPS Analysis ke OpenAI?"):
        print("Eksekusi dibatalkan.")
        return 0

    # 5. Jalankan service dan tampilkan prosesnya.
    emit_event, record_trace, traces = make_reporters()

    print("\n" + "=" * 70)
    print("PROSES")
    print("=" * 70)

    try:
        rps_data = await analyze_rps(
            rps_yaml,
            max_fix_attempts=max_fix_attempts,
            emit_event=emit_event,
            record_trace=record_trace,
            additional_prompt=additional_prompt,
        )
    except ValueError as exc:
        print(f"\n[GAGAL] Input tidak valid: {exc}")
        return 1
    except RPSAnalysisError as exc:
        print(f"\n[GAGAL] {exc.code} ({exc.reason_code}) setelah {exc.attempts} percobaan")
        if exc.__cause__ is not None:  # penyebab asli, mis. TypeError atau error API
            print(f"        Penyebab: {type(exc.__cause__).__name__}: {exc.__cause__}")
        print_traces(traces)
        return 1
    except Exception as exc:
        print(f"\n[GAGAL] {type(exc).__name__}: {exc}")
        print_traces(traces)
        return 1

    # 6. Tampilkan hasil JSON tervalidasi.
    output_data = rps_data.model_dump(mode="json")

    print("\n" + "=" * 70)
    print("[SUKSES] HASIL RPS STRUCTURED DATA")
    print("=" * 70)
    print(json.dumps(output_data, indent=2, ensure_ascii=False))

    # 7. Jejak percobaan.
    print_traces(traces)
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
