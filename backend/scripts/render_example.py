from pathlib import Path
from src.prompts.loader import render_prompt

SAMPLE = {
    "rps_yaml": "mata_kuliah:\n  kode: IF101\n  nama: Algoritma dan Pemrograman",
    "instructor_context_yaml": "nama: Dr. Budi\nkeahlian: Basis Data\ngaya_penyampaian: santai dan banyak contoh",
    "additional_prompt": "Gunakan contoh sehari-hari.",
    "output_schema": '{\n  "status": "success | partial | error"\n}',
}

out = render_prompt("default", "v1", SAMPLE)

Path("docs").mkdir(exist_ok=True)
Path("docs/contoh_render_default_v1.md").write_text(out, encoding="utf-8")
print(out)
