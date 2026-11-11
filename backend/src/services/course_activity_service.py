"""Aktivitas yang ditambahkan dosen dari halaman kursus (Assignment, Quiz, Text and media area).

- :meth:`CourseActivityService.create` membuat activity lewat function plugin
  ``local_capstonebridge`` yang sudah terpasang untuk eksekusi Moodle
  (``create_assign``, ``create_quiz``, ``create_page``). Text and media area
  dibuat sebagai Page: Moodle core tidak punya web service untuk label, dan
  Page tidak memerlukan pemasangan ulang plugin.
- :meth:`CourseActivityService.generate` menyusun draf isi activity dengan AI
  dari tiga referensi: materi minggu tersebut (isi section Moodle dan course
  plan), RPS kursus, dan file referensi pilihan dosen. Draf hanya mengisi
  formulir; tidak ada yang dibuat di Moodle sebelum dosen menyimpan.
"""

from __future__ import annotations

import html
import io
import json
import logging
import re
import uuid
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from src.schemas.course_activity import (
    ActivityModname,
    AssignmentDraftOutput,
    CreateActivityRequest,
    CreateActivityResponse,
    GenerateActivityResponse,
    LabelDraftOutput,
    QuizDraftOutput,
)
from src.services.content.illustrations import is_trusted_image_url, resolve_single_illustration
from src.services.llm.structured_output import make_openai_strict_schema
from src.services.moodle_html import figure_html, markdown_to_html, paragraphs_html
from src.services.moodle_integration_service import MoodleIntegrationService

__all__ = [
    "ActivityGenerationError",
    "CourseActivityService",
    "ReferenceFile",
    "UnsupportedReferenceFileError",
    "extract_reference_text",
]

logger = logging.getLogger(__name__)

CREATE_FUNCTIONS = {
    ActivityModname.ASSIGN: "local_capstonebridge_create_assign",
    ActivityModname.QUIZ: "local_capstonebridge_create_quiz",
    # Text and media area dibuat sebagai Page (lihat docstring modul).
    ActivityModname.LABEL: "local_capstonebridge_create_page",
}
PROMPT_NAME = "course_activity"
PROMPT_VERSION = "v1"
#: Batas teks referensi yang dikirim ke LLM (karakter) agar prompt tetap ringkas.
MAX_WEEK_CHARS = 12_000
MAX_RPS_CHARS = 8_000
MAX_FILE_CHARS = 15_000
MAX_REFERENCE_FILE_BYTES = 15 * 1024 * 1024
MAX_QUIZ_QUESTIONS = 30
_TAG = re.compile(r"<[^>]+>")
_SPACES = re.compile(r"\s+")

OUTPUT_MODELS: dict[ActivityModname, type[BaseModel]] = {
    ActivityModname.ASSIGN: AssignmentDraftOutput,
    ActivityModname.QUIZ: QuizDraftOutput,
    ActivityModname.LABEL: LabelDraftOutput,
}


class ActivityGenerationError(Exception):
    """Draf tidak dapat dibuat; ``public_message`` aman ditampilkan ke dosen."""

    def __init__(self, public_message: str) -> None:
        super().__init__(public_message)
        self.public_message = public_message


class UnsupportedReferenceFileError(ActivityGenerationError):
    pass


@dataclass(frozen=True)
class ReferenceFile:
    filename: str
    content: bytes


def _plain(markup: str | None) -> str:
    return _SPACES.sub(" ", html.unescape(_TAG.sub(" ", markup or ""))).strip()


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + " …(dipotong)"


def extract_reference_text(file: ReferenceFile) -> str:
    """Teks dari file referensi dosen: PDF, DOCX, PPTX, TXT, atau MD.

    Pustaka PDF/DOCX/PPTX ikut terpasang bersama konverter dokumen RPS
    (extra ``docling``); bila tidak tersedia di server, format tersebut ditolak
    dengan pesan yang jelas.
    """
    if len(file.content) > MAX_REFERENCE_FILE_BYTES:
        raise UnsupportedReferenceFileError("Ukuran file referensi maksimal 15 MB.")
    name = file.filename.lower()
    try:
        if name.endswith((".txt", ".md")):
            return file.content.decode("utf-8", errors="replace")
        if name.endswith(".pdf"):
            import pypdfium2 as pdfium  # type: ignore[import-not-found]

            document = pdfium.PdfDocument(file.content)
            try:
                return "\n".join(document[index].get_textpage().get_text_range() for index in range(len(document)))
            finally:
                document.close()
        if name.endswith(".docx"):
            import docx  # type: ignore[import-not-found]

            return "\n".join(paragraph.text for paragraph in docx.Document(io.BytesIO(file.content)).paragraphs)
        if name.endswith(".pptx"):
            import pptx  # type: ignore[import-not-found]

            presentation = pptx.Presentation(io.BytesIO(file.content))
            return "\n".join(
                shape.text_frame.text
                for slide in presentation.slides
                for shape in slide.shapes
                if getattr(shape, "has_text_frame", False)
            )
    except ImportError as exc:
        raise UnsupportedReferenceFileError(
            "Server belum mendukung pembacaan format file ini. Gunakan PDF, DOCX, PPTX, TXT, atau MD."
        ) from exc
    except Exception as exc:  # file rusak atau terenkripsi
        raise UnsupportedReferenceFileError("File referensi tidak dapat dibaca.") from exc
    raise UnsupportedReferenceFileError("Format file referensi harus PDF, DOCX, PPTX, TXT, atau MD.")


def _title_from_html(markup: str) -> str:
    """Nama Page dari awal teks (Text and media area boleh tanpa judul)."""
    text = _plain(markup)
    if not text:
        return "Teks dan media"
    return text if len(text) <= 60 else text[:57].rstrip() + "..."


def _assignment_intro_html(draft: AssignmentDraftOutput) -> str:
    parts = [markdown_to_html(draft.instructions_markdown)]
    if draft.expected_outputs:
        items = "".join(f"<li>{html.escape(item)}</li>" for item in draft.expected_outputs)
        parts.append(f"<h3>Luaran yang diharapkan</h3><ul>{items}</ul>")
    if draft.rubric:
        rows = "".join(
            f"<tr><td>{html.escape(row.criterion)}</td><td>{html.escape(row.description)}</td>"
            f"<td>{int(row.weight_percent)}%</td></tr>"
            for row in draft.rubric
        )
        parts.append(
            "<h3>Rubrik penilaian</h3><table><thead><tr><th>Kriteria</th><th>Deskripsi</th><th>Bobot</th></tr>"
            f"</thead><tbody>{rows}</tbody></table>"
        )
    return "".join(parts)


def _label_html(draft: LabelDraftOutput) -> str:
    body = markdown_to_html(draft.body_markdown)
    illustration = draft.illustration
    if illustration is not None and is_trusted_image_url(illustration.image_url):
        body += figure_html(
            illustration.image_url or "",
            illustration.caption,
            attribution=illustration.attribution,
            source_url=illustration.source_url,
        )
    return body


class CourseActivityService:
    def __init__(self, moodle: MoodleIntegrationService, *, llm=None, references=None) -> None:
        self._moodle = moodle
        self._llm = llm
        # ``references``: callable async (moodle_course_id, owner_id) -> (plan_week_lookup, rps_text);
        # disuntik route agar service ini tidak bergantung pada session database.
        self._references = references

    # --- Create -----------------------------------------------------------

    async def create(self, moodle_course_id: int, request: CreateActivityRequest) -> CreateActivityResponse:
        """Buat activity pada section ``request.section`` (section yang belum ada dibuat Moodle)."""
        await self._moodle.get_course(moodle_course_id)
        params: dict = {"courseid": moodle_course_id, "section": request.section}
        if request.modname is ActivityModname.ASSIGN:
            params |= {
                "name": request.name.strip(),
                "intro": request.intro,
                "duedate": request.duedate,
                "grade": request.grade,
                "onlinetext": int(request.onlinetext_enabled),
                "filesubmission": int(request.file_enabled),
                "maxfiles": request.file_maxfiles,
            }
        elif request.modname is ActivityModname.QUIZ:
            params |= {
                "name": request.name.strip(),
                "intro": request.intro,
                # create_quiz mewajibkan idnumber (juga dipakai sebagai kategori soal).
                "idnumber": f"capstone-manual-quiz-{uuid.uuid4().hex}",
                "timelimit": request.timelimit_minutes * 60,
                "attempts": request.attempts,
                "passpercent": request.passpercent,
                "shufflequestions": int(request.shufflequestions),
                "questions": [
                    {
                        "text": question.text if "<" in question.text else paragraphs_html(question.text),
                        "generalfeedback": question.generalfeedback
                        if "<" in question.generalfeedback
                        else paragraphs_html(question.generalfeedback),
                        "answers": [{"text": a.text.strip(), "correct": int(a.correct)} for a in question.answers],
                    }
                    for question in request.questions
                ],
            }
        else:
            params |= {"name": request.name.strip() or _title_from_html(request.text), "content": request.text}

        result = await self._moodle.client.call(CREATE_FUNCTIONS[request.modname], params)
        return CreateActivityResponse(
            cmid=int(result["cmid"]),
            modname=request.modname,
            section=request.section,
            created=int(result.get("created", 1)) == 1,
        )

    # --- Generate ---------------------------------------------------------

    async def _week_reference(self, moodle_course_id: int, section: int, plan_week: dict | None) -> tuple[str, list[str]]:
        contents = await self._moodle.get_course_contents(moodle_course_id, with_intros=True)
        target = next((s for s in contents.sections if s.section_number == section), None)
        parts: list[str] = []
        existing: list[str] = []
        if plan_week:
            parts.append("Rencana minggu (course plan):\n" + json.dumps(plan_week, ensure_ascii=False, indent=2))
        if target is not None:
            parts.append(f"Section LMS: {target.name or f'Pertemuan {section}'}")
            if target.summary:
                parts.append("Ringkasan section: " + _plain(target.summary))
            for module in target.modules:
                existing.append(f"{module.modname}: {module.name}")
                body = _plain(module.content or module.description)
                if body and module.modname in {"page", "label"}:
                    parts.append(f"Materi '{module.name}':\n{body}")
        return _clip("\n\n".join(parts), MAX_WEEK_CHARS), existing

    async def generate(
        self,
        moodle_course_id: int,
        *,
        owner_id: str,
        modname: ActivityModname,
        section: int,
        instruction: str = "",
        question_count: int = 10,
        difficulty: str = "sedang",
        use_week: bool = True,
        use_rps: bool = True,
        reference_file: ReferenceFile | None = None,
    ) -> GenerateActivityResponse:
        if self._llm is None:
            raise ActivityGenerationError("Layanan AI belum dikonfigurasi di server.")
        used: list[str] = []

        plan_week, rps_text = (None, "")
        if self._references is not None and (use_week or use_rps):
            plan_week, rps_text = await self._references(moodle_course_id, owner_id, section)

        week_text, existing = ("", [])
        if use_week:
            week_text, existing = await self._week_reference(moodle_course_id, section, plan_week)
            if week_text:
                used.append("Materi minggu ini")
        if use_rps and rps_text:
            used.append("RPS kursus")
        file_text = ""
        if reference_file is not None:
            file_text = _clip(extract_reference_text(reference_file).strip(), MAX_FILE_CHARS)
            if file_text:
                used.append(f"File: {reference_file.filename}")
        if not (week_text or (use_rps and rps_text) or file_text or instruction.strip()):
            raise ActivityGenerationError(
                "Belum ada referensi untuk minggu ini. Pilih file referensi atau tulis instruksi tambahan."
            )

        model = OUTPUT_MODELS[modname]
        count = max(1, min(int(question_count or 10), MAX_QUIZ_QUESTIONS))
        result = await self._llm.execute_prompt(
            prompt_name=PROMPT_NAME,
            version=PROMPT_VERSION,
            variables={
                "activity_kind": modname.value,
                "week_reference": week_text or "Tidak tersedia.",
                "rps_reference": _clip(rps_text, MAX_RPS_CHARS) if use_rps and rps_text else "Tidak tersedia.",
                "file_reference": file_text or "Tidak tersedia.",
                "existing_activities": "\n".join(f"- {item}" for item in existing) or "Belum ada.",
                "instructor_instruction": instruction.strip() or "Tidak ada instruksi tambahan.",
                "quiz_settings": f"Jumlah soal: {count}. Tingkat kesulitan: {difficulty}."
                if modname is ActivityModname.QUIZ
                else "Tidak relevan.",
            },
            output_schema=make_openai_strict_schema(model.model_json_schema()),
        )
        try:
            draft = model.model_validate(result.data)
        except ValidationError as exc:
            logger.warning("draf aktivitas %s tidak sesuai schema: %s", modname.value, exc)
            raise ActivityGenerationError("AI menghasilkan draf yang tidak valid. Coba generate ulang.") from exc

        if isinstance(draft, AssignmentDraftOutput):
            return GenerateActivityResponse(modname=modname, name=draft.name, intro=_assignment_intro_html(draft), references_used=used)
        if isinstance(draft, QuizDraftOutput):
            return GenerateActivityResponse(
                modname=modname,
                name=draft.name,
                intro=paragraphs_html(draft.description) if draft.description else "",
                questions=draft.questions[:count],
                references_used=used,
            )
        label = draft.model_copy(update={"illustration": await resolve_single_illustration(draft.illustration)})
        return GenerateActivityResponse(modname=modname, name=label.name, text=_label_html(label), references_used=used)

