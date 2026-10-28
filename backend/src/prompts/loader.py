from pathlib import Path
from string import Template
import yaml

PROMPTS_ROOT = Path(__file__).resolve().parent
DEFAULT_ADDITIONAL = "Tidak ada instruksi tambahan."

class PromptRenderError(Exception):
    pass

def render_prompt(name: str, version: str, variables: dict) -> str:
    base = PROMPTS_ROOT / name / version
    if not base.exists():
        raise PromptRenderError(f"Prompt {name}/{version} tidak ditemukan")

    meta = yaml.safe_load((base / "meta.yaml").read_text(encoding="utf-8"))
    missing = [v for v in meta["required_variables"] if v not in variables]
    if missing:
        raise PromptRenderError(f"Variabel wajib belum diisi: {missing}")

    values = dict(variables)
    values["additional_prompt"] = values.get("additional_prompt") or DEFAULT_ADDITIONAL

    template = Template((base / "template.md").read_text(encoding="utf-8"))
    try:
        return template.substitute(values)   # KeyError jika ada placeholder tak terisi
    except (KeyError, ValueError) as e:
        raise PromptRenderError(f"Gagal merender template: {e}")

    #buat function main.py -> buka file directory untuk upload file rps upload -> function untuk docling untuk convert ke yaml (function service -> rps -> yaml export) -> buat versi prompt dan versi non prompt
