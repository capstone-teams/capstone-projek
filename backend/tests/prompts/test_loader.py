import pytest
from src.prompts import loader
from src.prompts.loader import render_prompt, PromptRenderError, DEFAULT_ADDITIONAL

SAMPLE = {
    "rps_yaml": "mata_kuliah:\n  kode: IF101\n  nama: Algoritma",
    "instructor_context_yaml": "nama: Dr. Budi\nkeahlian: Basis Data",
    "additional_prompt": "Gunakan contoh sehari-hari.",
    "output_schema": '{"status": "success | partial | error"}',
}

REQUIRED = [
    "rps_yaml",
    "instructor_context_yaml",
    "output_schema",
]

TEMPLATE_TEXT = """<system_instruction>
Aturan umum.
</system_instruction>

<context>
<rps_yaml>
${rps_yaml}
</rps_yaml>

<instructor_context_yaml>
${instructor_context_yaml}
</instructor_context_yaml>

<additional_prompt>
${additional_prompt}
</additional_prompt>
</context>

<output_schema>
${output_schema}
</output_schema>
"""


def _write_prompt(root, name="tes", version="v1", template=TEMPLATE_TEXT):
    d = root / name / version
    d.mkdir(parents=True)
    required = "\n".join(f"  - {v}" for v in REQUIRED)
    (d / "meta.yaml").write_text(
        f"name: {name}\nversion: {version}\nrequired_variables:\n{required}\n",
        encoding="utf-8",
    )
    (d / "template.md").write_text(template, encoding="utf-8")
    return d


@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Template sementara, tidak bergantung pada file prompt asli."""
    _write_prompt(tmp_path)
    monkeypatch.setattr(loader, "PROMPTS_ROOT", tmp_path)
    return tmp_path


# ---------- Test terisolasi ----------

def test_render_success(isolated):
    out = render_prompt("tes", "v1", SAMPLE)
    assert "IF101" in out
    assert "Dr. Budi" in out
    assert "Gunakan contoh sehari-hari." in out
    assert '"status": "success | partial | error"' in out


def test_no_unrendered_placeholder(isolated):
    out = render_prompt("tes", "v1", SAMPLE)
    assert "${" not in out


def test_section_order(isolated):
    out = render_prompt("tes", "v1", SAMPLE)
    tags = ["<system_instruction>", "<context>", "<output_schema>"]
    idx = [out.index(t) for t in tags]
    assert idx == sorted(idx)


def test_additional_prompt_optional_missing(isolated):
    data = {k: v for k, v in SAMPLE.items() if k != "additional_prompt"}
    out = render_prompt("tes", "v1", data)
    assert DEFAULT_ADDITIONAL in out


@pytest.mark.parametrize("empty", [None, ""])
def test_additional_prompt_empty_uses_default(isolated, empty):
    data = {**SAMPLE, "additional_prompt": empty}
    out = render_prompt("tes", "v1", data)
    assert DEFAULT_ADDITIONAL in out


@pytest.mark.parametrize("missing_var", REQUIRED)
def test_missing_required_variable(isolated, missing_var):
    data = {k: v for k, v in SAMPLE.items() if k != missing_var}
    with pytest.raises(PromptRenderError) as exc:
        render_prompt("tes", "v1", data)
    assert missing_var in str(exc.value)


def test_unknown_version(isolated):
    with pytest.raises(PromptRenderError):
        render_prompt("tes", "v99", SAMPLE)


def test_unknown_prompt_name(isolated):
    with pytest.raises(PromptRenderError):
        render_prompt("tidak_ada", "v1", SAMPLE)


def test_extra_variables_are_ignored(isolated):
    out = render_prompt("tes", "v1", {**SAMPLE, "variabel_lain": "x"})
    assert "IF101" in out


def test_special_characters_in_values_are_safe(isolated):
    data = {
        **SAMPLE,
        "rps_yaml": "biaya: Rp$100 ${bukan_placeholder} {{juga_bukan}}",
        "output_schema": '{"a": {"b": [1, 2]}}',
    }
    out = render_prompt("tes", "v1", data)
    assert "Rp$100 ${bukan_placeholder} {{juga_bukan}}" in out
    assert '{"a": {"b": [1, 2]}}' in out


def test_template_with_unknown_placeholder_raises(tmp_path, monkeypatch):
    _write_prompt(tmp_path, template=TEMPLATE_TEXT + "\n${variabel_tidak_dikenal}\n")
    monkeypatch.setattr(loader, "PROMPTS_ROOT", tmp_path)
    with pytest.raises(PromptRenderError):
        render_prompt("tes", "v1", SAMPLE)


def test_template_with_stray_dollar_raises(tmp_path, monkeypatch):
    _write_prompt(tmp_path, template=TEMPLATE_TEXT + "\nHarga: $ 100\n")
    monkeypatch.setattr(loader, "PROMPTS_ROOT", tmp_path)
    with pytest.raises(PromptRenderError):
        render_prompt("tes", "v1", SAMPLE)


def test_input_variables_not_mutated(isolated):
    data = {k: v for k, v in SAMPLE.items() if k != "additional_prompt"}
    snapshot = dict(data)
    render_prompt("tes", "v1", data)
    assert data == snapshot


# ---------- Test terhadap template asli (prompts/default/v1) ----------

def test_real_default_v1_renders():
    out = render_prompt("default", "v1", SAMPLE)
    assert "IF101" in out
    assert "${" not in out


def test_real_default_v1_has_all_sections():
    out = render_prompt("default", "v1", SAMPLE)
    for tag in [
        "<system_instruction>", "</system_instruction>",
        "<context>", "</context>",
        "<output_schema>", "</output_schema>",
    ]:
        assert tag in out
