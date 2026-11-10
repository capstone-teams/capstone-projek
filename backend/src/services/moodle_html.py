"""Konversi teks hasil generation menjadi HTML yang aman untuk Moodle.

Dipakai oleh operasi Moodle (page dan assignment). Seluruh teks di-escape lebih
dulu, sehingga HTML mentah dari hasil generation tidak pernah ikut dirender.
Yang didukung: paragraf, baris baru, heading, list bertitik dan bernomor, blok
kode (```), tautan ``http(s)``, serta bold, italic, dan inline code.
"""

from __future__ import annotations

import html
import re

__all__ = ["inline_markdown", "markdown_to_html", "paragraphs_html"]

_BULLET = re.compile(r"^[-*]\s+(.*)$")
_NUMBERED = re.compile(r"^\d+[.)]\s+(.*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_FENCE = re.compile(r"^```")
#: Tautan Markdown; hanya ``http(s)`` supaya skema lain tidak pernah dirender.
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")


def markdown_to_html(text: str, *, heading_tag: str | None = None) -> str:
    """Konversi Markdown sederhana menjadi HTML.

    ``heading_tag`` memaksa semua heading memakai satu tag (misalnya ``h5`` untuk
    deskripsi assignment). Bila kosong, ``#`` menjadi ``h2``, ``##`` menjadi
    ``h3``, dan seterusnya sampai ``h6``.
    """
    blocks: list[str] = []
    paragraph: list[str] = []
    list_tag: str | None = None
    list_items: list[str] = []
    code_lines: list[str] | None = None

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append("<p>" + "<br>".join(inline_markdown(line) for line in paragraph) + "</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_tag
        if list_tag:
            items = "".join(f"<li>{inline_markdown(item)}</li>" for item in list_items)
            blocks.append(f"<{list_tag}>{items}</{list_tag}>")
            list_items.clear()
            list_tag = None

    for raw in text.strip().splitlines():
        if code_lines is not None:
            if _FENCE.match(raw.strip()):
                blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
                code_lines = None
            else:
                code_lines.append(raw)
            continue

        line = raw.strip()
        if _FENCE.match(line):
            flush_paragraph()
            flush_list()
            code_lines = []
            continue

        bullet, numbered, heading = _BULLET.match(line), _NUMBERED.match(line), _HEADING.match(line)
        if not line:
            flush_paragraph()
            flush_list()
        elif heading:
            flush_paragraph()
            flush_list()
            tag = heading_tag or f"h{min(len(heading.group(1)) + 1, 6)}"
            blocks.append(f"<{tag}>{inline_markdown(heading.group(2))}</{tag}>")
        elif bullet or numbered:
            flush_paragraph()
            tag = "ul" if bullet else "ol"
            if list_tag != tag:
                flush_list()
                list_tag = tag
            list_items.append((bullet or numbered).group(1))
        else:
            flush_list()
            paragraph.append(line)

    if code_lines is not None:  # blok kode tidak ditutup: tetap tampilkan isinya
        blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
    flush_paragraph()
    flush_list()
    return "".join(blocks)


def inline_markdown(text: str) -> str:
    """Escape satu baris teks lalu terapkan inline code, tautan, bold, italic."""
    escaped = html.escape(text.strip())
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = _LINK.sub(r'<a href="\2">\1</a>', escaped)
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])", r"<em>\1</em>", escaped)
    return escaped


def paragraphs_html(text: str) -> str:
    """Teks biasa menjadi paragraf HTML yang sudah di-escape (tanpa Markdown)."""
    parts = [part.strip() for part in text.strip().split("\n\n") if part.strip()]
    return "".join(f"<p>{html.escape(part)}</p>" for part in parts)