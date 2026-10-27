"""CLI interaktif untuk menguji prompt Ekstraksi RPS (RPS Analysis) OpenAI."""

import asyncio
import json
import sys
from pathlib import Path

# Memastikan root backend tersedia di sys.path
BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.config.settings import get_settings
from src.services.llm import LLMService, OpenAIProvider



OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "schema_version": {
            "type": "string"
        },
        "course": {
            "type": ["object", "null"],
            "properties": {
                "study_program": {
                    "type": ["string", "null"]
                },
                "name": {
                    "type": ["string", "null"]
                },
                "code": {
                    "type": ["string", "null"]
                },
                "credits": {
                    "type": ["integer", "null"]
                },
                "semester": {
                    "type": ["integer", "null"]
                },
                "description": {
                    "type": ["string", "null"]
                },
                "course_cluster": {
                    "type": ["string", "null"]
                },
                "prerequisites": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "prepared_at": {
                    "type": ["string", "null"]
                },
                "lecturers": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "authorization": {
                    "type": ["string", "null"]
                },
            },
            "required": [
                "study_program",
                "name",
                "code",
                "credits",
                "semester",
                "description",
                "course_cluster",
                "prerequisites",
                "prepared_at",
                "lecturers",
                "authorization",
            ],
            "additionalProperties": False,
        },
        "cpl": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["code", "description"],
                "additionalProperties": False,
            },
        },
        "cpmk": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "description": {"type": "string"},
                    "cpl_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["code", "description", "cpl_refs"],
                "additionalProperties": False,
            },
        },
        "sub_cpmk": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "description": {"type": "string"},
                    "cpmk_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["code", "description", "cpmk_refs"],
                "additionalProperties": False,
            },
        },
        "study_materials": {
            "type": "array",
            "items": {"type": "string"},
        },
        "weekly_plan": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "week": {"type": "integer"},
                    "week_type": {
                        "type": "string",
                        "enum": ["regular", "uts", "uas", "kuis"],
                    },
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "cpmk": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "sub_cpmk": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "teaching_method": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "media": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                    "assessment": {
                        "type": ["object", "null"],
                        "properties": {
                            "type": {"type": ["string", "null"]},
                            "description": {
                                "type": ["string", "null"]
                            },
                            "weight_percent": {
                                "type": ["number", "null"]
                            },
                        },
                        "required": [
                            "type",
                            "description",
                            "weight_percent",
                        ],
                        "additionalProperties": False,
                    },
                },
                "required": [
                    "week",
                    "week_type",
                    "topics",
                    "cpmk",
                    "sub_cpmk",
                    "teaching_method",
                    "media",
                    "assessment",
                ],
                "additionalProperties": False,
            },
        },
        "assessments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "component": {"type": "string"},
                    "weight_percent": {
                        "type": ["number", "null"]
                    },
                    "cpmk_refs": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "component",
                    "weight_percent",
                    "cpmk_refs",
                ],
                "additionalProperties": False,
            },
        },
        "references": {
            "type": "object",
            "properties": {
                "main": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "supporting": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["main", "supporting"],
            "additionalProperties": False,
        },
        "media": {
            "type": "object",
            "properties": {
                "software": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "hardware": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["software", "hardware"],
            "additionalProperties": False,
        },
        "extraction": {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "object",
                    "properties": {
                        "course": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "cpl": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "cpmk": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "sub_cpmk": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "study_materials": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "weekly_plan": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "assessments": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "references": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                        "media": {
                            "type": "string",
                            "enum": ["found", "partial", "not_found"],
                        },
                    },
                    "required": [
                        "course",
                        "cpl",
                        "cpmk",
                        "sub_cpmk",
                        "study_materials",
                        "weekly_plan",
                        "assessments",
                        "references",
                        "media",
                    ],
                    "additionalProperties": False,
                },
                "warnings": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "source_pages": {
                    "type": "object",
                    "properties": {
                        "course": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "cpl": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "cpmk": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "sub_cpmk": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "study_materials": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "weekly_plan": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "assessments": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "references": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "media": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                    },
                    "required": [
                        "course",
                        "cpl",
                        "cpmk",
                        "sub_cpmk",
                        "study_materials",
                        "weekly_plan",
                        "assessments",
                        "references",
                        "media",
                    ],
                    "additionalProperties": False,
                },
            },
            "required": ["sections", "warnings", "source_pages"],
            "additionalProperties": False,
        },
    },
    "required": [
        "schema_version",
        "course",
        "cpl",
        "cpmk",
        "sub_cpmk",
        "study_materials",
        "weekly_plan",
        "assessments",
        "references",
        "media",
        "extraction",
    ],
    "additionalProperties": False,
}


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
            return path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"[GAGAL] Tidak bisa membaca file: {e}")


def ask_yes_no(question: str) -> bool:
    """Meminta jawaban ya/tidak."""
    while True:
        answer = input(f"{question} [y/n]: ").strip().lower()

        if answer in ("y", "ya", "yes"):
            return True
        if answer in ("n", "tidak", "no"):
            return False

        print("Masukkan y atau n.")


def ask_optional_text(label: str) -> str | None:
    """Meminta teks opsional."""
    while True:
        value = input(f"{label}: ").strip()

        if value.lower() == "skip":
            return None
        if value:
            return value

        print(
            "Teks tidak boleh kosong. "
            "Masukkan instruksi atau ketik 'skip'."
        )


def read_task_instruction() -> str:
    """Membaca instruksi dari file Markdown atau teks manual."""
    while True:
        value = input("Instruksi tugas / Path file: ").strip()

        if value.lower() == "skip":
            return ""

        if not value:
            print("Masukkan instruksi, path file, atau ketik 'skip'.")
            continue

        path = Path(value).expanduser()

        # Jika berupa path file Markdown yang tersedia, baca isinya.
        if path.suffix.lower() == ".md":
            if not path.is_absolute():
                path = Path.cwd() / path

            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                    print(f"[SUKSES] File instruksi dibaca: {path}")
                    return content
                except OSError as e:
                    print(f"[GAGAL] Gagal membaca file instruksi: {e}")
                    continue

            # Jangan diam-diam mengirim path yang salah sebagai instruksi.
            print(f"[GAGAL] File instruksi tidak ditemukan: {path}")
            print("Masukkan path yang benar atau ketik 'skip'.")
            continue

        # Selain path .md, perlakukan input sebagai teks instruksi manual.
        return value


def markdown_value(value) -> str:
    """Mengubah nilai menjadi teks Markdown yang aman untuk tabel sederhana."""
    if value is None or value == "":
        return "-"

    if isinstance(value, list):
        return ", ".join(str(item) for item in value) or "-"

    return str(value).replace("\n", " ").strip() or "-"


def save_result_as_markdown(data: dict) -> Path:
    """Menyimpan seluruh bagian hasil ekstraksi RPS ke file Markdown."""
    import datetime

    output_dir = Path.cwd() / "hasil_ekstraksi_rps"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"hasil_ekstraksi_rps_{timestamp}.md"

    lines = [
        "# Hasil Ekstraksi RPS",
        "",
        f"**Schema Version:** {markdown_value(data.get('schema_version'))}",
        "",
        "## 1. Informasi Mata Kuliah",
        "",
    ]

    course = data.get("course") or {}
    course_fields = [
        ("Nama Mata Kuliah", course.get("name")),
        ("Kode Mata Kuliah", course.get("code")),
        ("SKS", course.get("credits")),
        ("Semester", course.get("semester")),
        ("Deskripsi", course.get("description")),
    ]

    for label, value in course_fields:
        lines.append(f"- **{label}:** {markdown_value(value)}")

    lines.extend(["", "## 2. Capaian Pembelajaran Lulusan (CPL)", ""])

    cpl_items = data.get("cpl", [])
    if cpl_items:
        for item in cpl_items:
            lines.append(
                f"- **{markdown_value(item.get('id'))}:** "
                f"{markdown_value(item.get('description'))}"
            )
    else:
        lines.append("- Tidak ada data CPL.")

    lines.extend([
        "",
        "## 3. Capaian Pembelajaran Mata Kuliah (CPMK)",
        "",
    ])

    cpmk_items = data.get("cpmk", [])
    if cpmk_items:
        for item in cpmk_items:
            lines.extend([
                f"### {markdown_value(item.get('id'))}",
                "",
                markdown_value(item.get("description")),
                "",
                f"- **CPL terkait:** "
                f"{markdown_value(item.get('cpl_ids', []))}",
                "",
            ])
    else:
        lines.append("- Tidak ada data CPMK.")

    lines.extend(["", "## 4. Sub-CPMK", ""])

    sub_cpmk_items = data.get("sub_cpmk", [])
    if sub_cpmk_items:
        for item in sub_cpmk_items:
            lines.extend([
                f"### {markdown_value(item.get('id'))}",
                "",
                markdown_value(item.get("description")),
                "",
                f"- **CPMK terkait:** "
                f"{markdown_value(item.get('cpmk_ids', []))}",
                "",
            ])
    else:
        lines.append("- Tidak ada data Sub-CPMK.")

    lines.extend(["", "## 5. Topik Pembelajaran", ""])

    for item in data.get("topics", []):
        lines.append(
            f"- **{markdown_value(item.get('id'))}:** "
            f"{markdown_value(item.get('name'))}"
        )

    if not data.get("topics"):
        lines.append("- Tidak ada data topik.")

    lines.extend(["", "## 6. Media Pembelajaran", ""])

    for item in data.get("media", []):
        lines.extend([
            f"### {markdown_value(item.get('id'))}. "
            f"{markdown_value(item.get('name'))}",
            "",
            f"- **Jenis:** {markdown_value(item.get('type'))}",
            f"- **Deskripsi:** "
            f"{markdown_value(item.get('description'))}",
            "",
        ])

    if not data.get("media"):
        lines.append("- Tidak ada data media.")

    lines.extend(["", "## 7. Rencana Pembelajaran Mingguan", ""])

    weeks = sorted(data.get("weeks", []), key=lambda item: item["week"])

    if weeks:
        for week in weeks:
            lines.extend([
                f"### Minggu {week['week']} "
                f"({markdown_value(week.get('week_type'))})",
                "",
                f"- **Topik:** "
                f"{markdown_value(week.get('topics', []))}",
                f"- **CPMK:** "
                f"{markdown_value(week.get('cpmk', []))}",
                f"- **Sub-CPMK:** "
                f"{markdown_value(week.get('sub_cpmk', []))}",
                f"- **Metode mengajar:** "
                f"{markdown_value(week.get('teaching_method', []))}",
                f"- **Media:** "
                f"{markdown_value(week.get('media', []))}",
            ])

            assessment = week.get("assessment")
            if assessment:
                weight = assessment.get("weight_percent")
                weight_text = (
                    f"{weight}%"
                    if weight is not None
                    else "-"
                )

                lines.extend([
                    "",
                    "**Penilaian Mingguan**",
                    "",
                    f"- **Jenis:** "
                    f"{markdown_value(assessment.get('type'))}",
                    f"- **Deskripsi:** "
                    f"{markdown_value(assessment.get('description'))}",
                    f"- **Bobot:** {weight_text}",
                ])

            lines.append("")
    else:
        lines.append("- Tidak ada data rencana mingguan.")

    lines.extend(["", "## 8. Metode Pengajaran", ""])

    for method in data.get("teaching_methods", []):
        lines.append(f"- {markdown_value(method)}")

    if not data.get("teaching_methods"):
        lines.append("- Tidak ada data metode pengajaran.")

    lines.extend(["", "## 9. Penilaian", ""])

    assessments = data.get("assessments", [])
    if assessments:
        for item in assessments:
            weight = item.get("weight_percent")
            weight_text = f"{weight}%" if weight is not None else "-"

            lines.extend([
                f"### {markdown_value(item.get('id'))}",
                "",
                f"- **Jenis:** {markdown_value(item.get('type'))}",
                f"- **Minggu:** {markdown_value(item.get('week'))}",
                f"- **Bobot:** {weight_text}",
                f"- **Deskripsi:** "
                f"{markdown_value(item.get('description'))}",
                "",
            ])
    else:
        lines.append("- Tidak ada data penilaian.")

    lines.extend(["", "## 10. Referensi", ""])

    references = data.get("references", [])
    if references:
        for item in references:
            lines.append(
                f"- **{markdown_value(item.get('id'))}:** "
                f"{markdown_value(item.get('citation'))}"
            )

            authors = item.get("authors")
            year = item.get("year")
            source = item.get("source")

            details = []
            if authors:
                details.append(f"Penulis: {authors}")
            if year is not None:
                details.append(f"Tahun: {year}")
            if source:
                details.append(f"Sumber: {source}")

            if details:
                lines.append(f"  - {' | '.join(details)}")
    else:
        lines.append("- Tidak ada data referensi.")

    lines.extend(["", "## 11. Catatan Ekstraksi", ""])

    extraction = data.get("extraction") or {}
    warnings = extraction.get("warnings", [])

    if warnings:
        for warning in warnings:
            lines.append(f"- {markdown_value(warning)}")
    else:
        lines.append("- Tidak ada peringatan ekstraksi.")

    lines.append("")

    output_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    return output_path


async def main() -> int:
    settings = get_settings()
    provider = OpenAIProvider()

    print("=" * 70)
    print("CLI: MOODLE AGENTIC AI - RPS EXTRACTION TEST")
    print("=" * 70)

    if not provider.is_configured():
        print("[GAGAL] OPENAI_API_KEY belum dikonfigurasi di backend/.env.")
        return 1

    print(f"Provider : {provider.provider_name} ({provider.label})")
    print(f"Model    : {provider.model}")
    print("=" * 70)

    # 1. Input RPS
    print("\n[1] INPUT DATA MENTAH")
    rps_yaml = read_yaml_file("RPS (YAML)")

    # 2. Task instruction
    print("\n[2] TASK INSTRUCTION")
    print(
        "Masukkan path file instruction.md, "
        "teks instruksi manual, atau ketik 'skip'."
    )

    if ask_yes_no("Tambahkan task instruction?"):
        task_instruction = read_task_instruction()
    else:
        task_instruction = ""

    # 3. Siapkan variabel prompt
    variables = {
        "rps_yaml": rps_yaml,
        "task_instruction": task_instruction,
    }

    print("\n" + "=" * 70)
    print("KONFIRMASI INPUT EKSTRAKSI")
    print("=" * 70)
    print("RPS (YAML)       : berhasil dibaca")
    print(
        "Task instruction : "
        f"{'Ya (Teks/File terlampir)' if task_instruction else 'Tidak'}"
    )

    if not ask_yes_no("\nJalankan prompt ke OpenAI?"):
        print("Eksekusi dibatalkan.")
        return 0

    service = LLMService(provider)

    try:
        result = await service.execute_prompt(
            prompt_name="rps_analysis",
            version="v1",
            variables=variables,
            output_schema=OUTPUT_SCHEMA,
        )
    except Exception as e:
        print(f"\n[GAGAL] {type(e).__name__}: {e}")
        return 1

    # 4. Tampilkan hasil JSON
    print("\n" + "=" * 70)
    print("[SUKSES] HASIL STRUCTURED DATA (JSON)")
    print("=" * 70)
    print(json.dumps(result.data, indent=2, ensure_ascii=False))

    # 5. Simpan hasil ke Markdown jika diminta
    print("\n" + "=" * 70)
    print("SIMPAN HASIL EKSTRAKSI")
    print("=" * 70)

    if ask_yes_no("Simpan hasil ekstraksi sebagai file Markdown?"):
        try:
            output_path = save_result_as_markdown(result.data)
            print("\n[SUKSES] File Markdown berhasil disimpan.")
            print(f"Lokasi: {output_path.resolve()}")
        except OSError as e:
            print(f"\n[GAGAL] Tidak bisa menyimpan file Markdown: {e}")

    # 6. Metadata pemanggilan
    metadata = result.metadata

    print("\n" + "-" * 70)
    print("METADATA PEMANGGILAN")
    print("-" * 70)
    print(f"Prompt       : {metadata.prompt_name}/{metadata.prompt_version}")
    print(f"Input Token  : {metadata.input_tokens}")
    print(f"Output Token  : {metadata.output_tokens}")
    print(f"Total token  : {metadata.total_tokens}")
    print(f"Durasi       : {metadata.duration_ms:.2f} ms")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
