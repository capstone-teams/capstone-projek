"""Ilustrasi materi: diagram Mermaid (Kroki) dan foto berlisensi (Wikimedia Commons)."""

import base64
import zlib

import httpx
import pytest

from src.schemas.content import IllustrationKind, LearningMaterialData, MaterialIllustration
from src.services.content.illustrations import (
    is_trusted_image_url,
    kroki_url,
    resolve_illustration,
    resolve_material_illustrations,
)
from src.services.moodle_page_service import LearningMaterialPage, render_material_html


def _commons_page(index, *, mime="image/jpeg", license_name="CC BY-SA 4.0", url="https://upload.wikimedia.org/a.jpg"):
    return {
        "index": index,
        "imageinfo": [
            {
                "mime": mime,
                "thumburl": url,
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:A.jpg",
                "extmetadata": {
                    "LicenseShortName": {"value": license_name},
                    "Artist": {"value": "<a href='x'>Jane Doe</a>"},
                },
            }
        ],
    }


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_kroki_url_encodes_mermaid_with_deflate_base64():
    url = kroki_url("flowchart TD\n  A --> B")
    encoded = url.rsplit("/", 1)[1]
    assert url.startswith("https://kroki.io/mermaid/svg/")
    assert zlib.decompress(base64.urlsafe_b64decode(encoded)).decode() == "flowchart TD\n  A --> B"


def test_trusted_image_hosts_only():
    assert is_trusted_image_url("https://kroki.io/mermaid/svg/abc")
    assert is_trusted_image_url("https://upload.wikimedia.org/x.png")
    assert not is_trusted_image_url("http://upload.wikimedia.org/x.png")
    assert not is_trusted_image_url("https://evil.example/x.png")
    assert not is_trusted_image_url(None)


@pytest.mark.asyncio
async def test_diagram_is_kept_only_when_kroki_renders_svg():
    item = MaterialIllustration(kind=IllustrationKind.DIAGRAM, caption="Alur", mermaid="flowchart TD\nA-->B", image_url="https://evil.example/x.png")

    async with _client(lambda request: httpx.Response(200, headers={"content-type": "image/svg+xml"}, text="<svg/>")) as client:
        resolved = await resolve_illustration(item, client=client)
    assert resolved is not None
    assert resolved.image_url == kroki_url("flowchart TD\nA-->B")  # URL dari LLM diganti
    assert resolved.attribution == "Diagram: Generator AI"

    async with _client(lambda request: httpx.Response(400, text="syntax error")) as client:
        assert await resolve_illustration(item, client=client) is None


@pytest.mark.asyncio
async def test_photo_picks_first_freely_licensed_bitmap_with_attribution():
    item = MaterialIllustration(kind=IllustrationKind.PHOTO, caption="Kabel serat optik", image_query="fiber optic cable")
    payload = {
        "query": {
            "pages": {
                "1": _commons_page(1, license_name="CC BY-NC 2.0", url="https://upload.wikimedia.org/nc.jpg"),
                "2": _commons_page(2, mime="image/svg+xml", url="https://upload.wikimedia.org/x.svg"),
                "3": _commons_page(3, license_name="CC BY-SA 4.0", url="https://upload.wikimedia.org/ok.jpg"),
            }
        }
    }
    seen = {}

    def handler(request):
        seen["query"] = request.url.params["gsrsearch"]
        return httpx.Response(200, json=payload)

    async with _client(handler) as client:
        resolved = await resolve_illustration(item, client=client)
    assert seen["query"] == "fiber optic cable filetype:bitmap"
    assert resolved.image_url == "https://upload.wikimedia.org/ok.jpg"
    assert resolved.source_url == "https://commons.wikimedia.org/wiki/File:A.jpg"
    assert resolved.attribution == "Foto: Jane Doe, CC BY-SA 4.0, via Wikimedia Commons"


@pytest.mark.asyncio
async def test_network_errors_drop_only_the_illustration():
    item = MaterialIllustration(kind=IllustrationKind.PHOTO, caption="x", image_query="router")

    def handler(request):
        raise httpx.ConnectError("offline")

    async with _client(handler) as client:
        assert await resolve_illustration(item, client=client) is None


@pytest.mark.asyncio
async def test_resolve_material_keeps_sections_and_old_data_without_illustrations():
    material = LearningMaterialData.model_validate(
        {
            "learning_objectives": ["Memahami normalisasi"],
            "sections": [{"heading": "Pengantar", "body_markdown": "Isi."}],  # data lama tanpa illustration
            "references": [],
            "traceability": {"week_number": 1, "sub_cpmk_codes": ["S1"], "weekly_plan_ref": "w1"},
        }
    )
    assert material.sections[0].illustration is None
    assert await resolve_material_illustrations(material) is material


def test_page_html_renders_trusted_figures_and_escapes_text():
    data = LearningMaterialData.model_validate(
        {
            "learning_objectives": ["Tujuan <1>"],
            "sections": [
                {
                    "heading": "Alur",
                    "body_markdown": "Teks **tebal**.",
                    "illustration": {
                        "kind": "DIAGRAM",
                        "caption": "Diagram \"alur\"",
                        "mermaid": "flowchart TD\nA-->B",
                        "image_url": "https://kroki.io/mermaid/svg/abc",
                        "attribution": "Diagram: Generator AI",
                    },
                },
                {
                    "heading": "Tidak dipercaya",
                    "body_markdown": "Isi.",
                    "illustration": {"kind": "PHOTO", "caption": "x", "image_url": "https://evil.example/x.png"},
                },
            ],
            "references": [],
            "traceability": {"week_number": 1, "sub_cpmk_codes": ["S1"], "weekly_plan_ref": "w1"},
        }
    )
    page_html = render_material_html(data)
    assert "<h3>Tujuan Pembelajaran</h3><ul><li>Tujuan &lt;1&gt;</li></ul>" in page_html
    assert '<img src="https://kroki.io/mermaid/svg/abc" alt="Diagram &quot;alur&quot;"' in page_html
    assert "<figcaption>Diagram &quot;alur&quot;<br><small>Diagram: Generator AI</small></figcaption>" in page_html
    assert "evil.example" not in page_html
    assert LearningMaterialPage.from_content("c1", "Judul", data.model_dump(mode="json")).content_html == page_html
