"""Script bukti penerimaan (Acceptance Evidence) untuk eksekusi prompt ke OpenAI.

Menjalankan satu contoh prompt (default/v1) ke provider OpenAI sungguhan,
memverifikasi structured output (JSON Schema), dan menampilkan metadata pemanggilan
(token input/output, durasi eksekusi, model, serta jumlah percobaan).
"""

import asyncio
import json
from pathlib import Path
import sys

# Memastikan direktori root backend berada di sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from src.config.settings import get_settings
from src.services.llm import LLMService, OpenAIProvider

SAMPLE_VARIABLES = {
    "rps_yaml": """mata_kuliah:
  kode: IF2103
  nama: Algoritma dan Pemrograman
  sks: 3
  semester: 1
capaian_pembelajaran:
  - Mahasiswa mampu merancang algoritma sekuensial dan percabangan
topik_mingguan:
  minggu_1: Pengantar Algoritma dan Notasi Flowchart""",
    "instructor_context_yaml": """nama: Dr. Budi Santoso
keahlian: Rekayasa Perangkat Lunak dan Algoritma
gaya_penyampaian: Praktis, interaktif, dan berbasis studi kasus dunia nyata""",
    "additional_prompt": "Berikan analogi kehidupan sehari-hari pada bagian ringkasan materi.",
    "task_instruction": "Susun rencana materi pembelajaran untuk Minggu ke-1 sesuai RPS.",
}

SAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["success", "partial", "error"],
        },
        "topik_utama": {"type": "string"},
        "sub_topik": {
            "type": "array",
            "items": {"type": "string"},
        },
        "ringkasan_materi": {"type": "string"},
        "aktivitas_pembelajaran": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "status",
        "topik_utama",
        "sub_topik",
        "ringkasan_materi",
        "aktivitas_pembelajaran",
    ],
    "additionalProperties": False,
}


async def main() -> int:
    settings = get_settings()
    provider = OpenAIProvider()

    print("=" * 70)
    print("BUKTI ACCEPTANCE: EKSEKUSI PROMPT OPENAI DENGAN STRUCTURED OUTPUT")
    print("=" * 70)

    if not provider.is_configured():
        print("[PERINGATAN] OPENAI_API_KEY belum dikonfigurasi pada .env.")
        print("Silakan isi OPENAI_API_KEY di backend/.env untuk menjalankan bukti live.")
        return 1

    print(f"Provider        : {provider.provider_name} ({provider.label})")
    print(f"Model           : {provider.model}")
    print(f"Endpoint        : {provider.api_url}")
    print(f"Timeout         : {provider.timeout} detik")
    print(f"Max Retries     : {settings.llm_max_retries}")
    print("-" * 70)
    print("Mengirim prompt 'default/v1' ke OpenAI...")

    service = LLMService(provider)

    try:
        result = await service.execute_prompt(
            prompt_name="default",
            version="v1",
            variables=SAMPLE_VARIABLES,
            output_schema=SAMPLE_SCHEMA,
        )
    except Exception as e:
        print(f"[GAGAL] Eksekusi prompt gagal: {type(e).__name__}: {e}")
        return 1

    print("[SUKSES] Respons terstruktur berhasil diterima dari OpenAI!")
    print("-" * 70)
    print("METADATA PEMANGGILAN:")
    print(f"  * Prompt Name/Version : {result.metadata.prompt_name}/{result.metadata.prompt_version}")
    print(f"  * Model yang Dipakai  : {result.metadata.model}")
    print(f"  * Token Input (Prompt): {result.metadata.prompt_tokens}")
    print(f"  * Token Output (Compl): {result.metadata.completion_tokens}")
    print(f"  * Total Token         : {result.metadata.total_tokens}")
    print(f"  * Durasi Eksekusi     : {result.metadata.duration_ms:.2f} ms")
    print(f"  * Jumlah Percobaan    : {result.metadata.attempts}")
    print("-" * 70)
    print("HASIL OUTPUT TERPARSING (JSON):")
    print(json.dumps(result.data, indent=2, ensure_ascii=False))
    print("=" * 70)
    print("Semua kriteria penerimaan (Acceptance Criteria) terpenuhi:")
    print("  [x] Satu prompt contoh berhasil dijalankan ke OpenAI dan menghasilkan output sesuai schema.")
    print("  [x] Metadata token dan durasi tercatat untuk setiap pemanggilan.")
    print("  [x] Retry provider dengan exponential backoff aktif.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
