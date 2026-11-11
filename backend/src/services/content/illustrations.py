"""Ilustrasi materi pembelajaran: diagram Mermaid dan gambar berlisensi bebas.

LLM menulis rencana ilustrasi per section (``MaterialIllustration``): kode
Mermaid untuk diagram, atau kata kunci untuk foto. Modul ini mengubahnya
menjadi gambar yang benar-benar dapat ditampilkan:

- ``DIAGRAM``: kode Mermaid dirender oleh layanan Kroki menjadi SVG. Kode
  diperiksa sekali saat generation; diagram yang tidak dapat dirender dibuang.
- ``PHOTO``: dicari di Wikimedia Commons. Hanya gambar berlisensi bebas
  (Creative Commons atau domain publik) yang dipakai, lengkap dengan atribusi
  dan tautan sumber sesuai syarat lisensinya.

URL dari LLM tidak pernah dipakai. Kegagalan jaringan atau hasil kosong hanya
menghapus ilustrasi section tersebut — generation konten tidak pernah gagal
karena ilustrasi.
"""

from __future__ import annotations

import base64
import html
import logging
import re
import zlib
from urllib.parse import urlparse

import httpx

from src.config.settings import get_settings
from src.schemas.content import IllustrationKind, MaterialIllustration

__all__ = [
    "illustration_hosts",
    "is_trusted_image_url",
    "kroki_url",
    "resolve_illustration",
    "resolve_material_illustrations",
    "resolve_single_illustration",
]

logger = logging.getLogger(__name__)

#: Wikimedia meminta User-Agent yang menjelaskan klien (https://meta.wikimedia.org/wiki/User-Agent_policy).
USER_AGENT = "AgenticLMS-ContentGenerator/1.0 (educational content generator)"
TIMEOUT_SECONDS = 10.0
MAX_MERMAID_CHARS = 4000
WIKIMEDIA_IMAGE_HOST = "upload.wikimedia.org"
_FREE_LICENSE = re.compile(r"^(cc0|cc[ -]by|public domain|pd\b|pd-)", re.IGNORECASE)
_NON_FREE = re.compile(r"\b(nc|nd)\b", re.IGNORECASE)
_TAG = re.compile(r"<[^>]+>")


def _kroki_base() -> str:
    return (get_settings().KROKI_BASE_URL or "https://kroki.io").rstrip("/")


def illustration_hosts() -> set[str]:
    """Host gambar yang boleh muncul di HTML materi (diperiksa ulang saat render)."""
    hosts = {WIKIMEDIA_IMAGE_HOST}
    kroki_host = urlparse(_kroki_base()).hostname
    if kroki_host:
        hosts.add(kroki_host)
    return hosts


def is_trusted_image_url(url: str | None) -> bool:
    """URL ``https`` dari host ilustrasi yang diizinkan."""
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in illustration_hosts()


def kroki_url(mermaid: str) -> str:
    """URL SVG Kroki untuk kode Mermaid (deflate + base64 url-safe, sesuai dokumentasi Kroki)."""
    encoded = base64.urlsafe_b64encode(zlib.compress(mermaid.encode("utf-8"), 9)).decode("ascii")
    return f"{_kroki_base()}/mermaid/svg/{encoded}"


def _plain(text: str | None) -> str:
    return html.unescape(_TAG.sub("", text or "")).strip()


async def _diagram(client: httpx.AsyncClient, item: MaterialIllustration) -> MaterialIllustration | None:
    source = (item.mermaid or "").strip()
    if not source or len(source) > MAX_MERMAID_CHARS:
        return None
    url = kroki_url(source)
    response = await client.get(url)
    if response.status_code != 200 or "svg" not in response.headers.get("content-type", ""):
        logger.info("diagram Mermaid tidak dapat dirender (status %s)", response.status_code)
        return None
    return item.model_copy(update={"image_url": url, "source_url": None, "attribution": "Diagram: Generator AI"})


async def _photo(client: httpx.AsyncClient, item: MaterialIllustration) -> MaterialIllustration | None:
    query = (item.image_query or "").strip()
    if not query:
        return None
    response = await client.get(
        get_settings().WIKIMEDIA_API_URL,
        params={
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{query} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": 8,
            "prop": "imageinfo",
            "iiprop": "url|mime|extmetadata",
            "iiurlwidth": 960,
        },
    )
    if response.status_code != 200:
        return None
    pages = sorted((response.json().get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for page in pages:
        info = (page.get("imageinfo") or [{}])[0]
        if info.get("mime") not in {"image/jpeg", "image/png"}:
            continue
        meta = info.get("extmetadata") or {}
        license_name = _plain((meta.get("LicenseShortName") or {}).get("value"))
        if not _FREE_LICENSE.match(license_name) or _NON_FREE.search(license_name):
            continue
        image_url = info.get("thumburl") or info.get("url")
        if not is_trusted_image_url(image_url):
            continue
        artist = _plain((meta.get("Artist") or {}).get("value")) or "Tidak diketahui"
        return item.model_copy(
            update={
                "image_url": image_url,
                "source_url": info.get("descriptionurl"),
                "attribution": f"Foto: {artist[:120]}, {license_name}, via Wikimedia Commons",
            }
        )
    return None


async def resolve_illustration(
    item: MaterialIllustration | None, *, client: httpx.AsyncClient
) -> MaterialIllustration | None:
    """Ilustrasi yang siap ditampilkan, atau ``None`` bila tidak dapat dipenuhi."""
    if item is None:
        return None
    # Field hasil resolusi dari LLM dibuang lebih dulu.
    item = item.model_copy(update={"image_url": None, "source_url": None, "attribution": None})
    try:
        if item.kind is IllustrationKind.DIAGRAM:
            return await _diagram(client, item)
        if item.kind is IllustrationKind.PHOTO:
            return await _photo(client, item)
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("ilustrasi %s dilewati: %s", item.kind.value, exc)
    return None


async def resolve_material_illustrations(material, *, client: httpx.AsyncClient | None = None):
    """Selesaikan ilustrasi setiap section pada output learning material.

    ``material`` adalah ``LearningMaterialOutput`` (atau model lain dengan
    ``sections``); model baru dikembalikan, model asli tidak diubah.
    """
    if not get_settings().ILLUSTRATIONS_ENABLED:
        return material
    sections = getattr(material, "sections", None) or []
    if not any(section.illustration for section in sections):
        return material

    own_client = client is None
    client = client or httpx.AsyncClient(timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}, follow_redirects=True)
    try:
        resolved = []
        for section in sections:
            illustration = await resolve_illustration(section.illustration, client=client)
            resolved.append(section.model_copy(update={"illustration": illustration}))
    finally:
        if own_client:
            await client.aclose()
    return material.model_copy(update={"sections": resolved})


async def resolve_single_illustration(item: MaterialIllustration | None) -> MaterialIllustration | None:
    """Selesaikan satu ilustrasi (mis. pada draf Text and media area) dengan client sendiri."""
    if item is None or not get_settings().ILLUSTRATIONS_ENABLED:
        return None
    async with httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    ) as client:
        return await resolve_illustration(item, client=client)
