import json
from functools import lru_cache
from pathlib import Path
from typing import List, Union
from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent

# Accepted aliases for LLM_PROVIDER ("google" is a legacy spelling of "gemini").
LLM_PROVIDER_ALIASES = {"google": "gemini"}

# Mode TableFormer Docling yang didukung (BE-05.2). Didefinisikan di sini supaya
# konfigurasi yang salah gagal saat startup — bukan saat request pertama —
# sementara adapter Docling tetap memakai daftar yang sama (layer `services/`
# boleh mengimpor `config/`, bukan sebaliknya).
RPS_TABLE_MODES = ("accurate", "fast")

# Nilai bawaan konfigurasi RPS (BE-05). Diletakkan di luar kelas ``Settings``
# dengan sengaja: seluruh field Settings hanya berisi nilai yang benar-benar
# dikonfigurasi (default-nya kosong), dan nilai bawaan diterapkan oleh property.
# Konvensi ini menjaga ``tests/test_config.py`` (tidak ada nilai yang
# ter-hardcode pada field Settings) sekaligus membuat tempat nilai bawaan hanya
# satu.
DEFAULT_RPS_STORAGE_DIR = BACKEND_DIR / "var" / "rps"
DEFAULT_RPS_MAX_UPLOAD_BYTES = 20 * 1024 * 1024
DEFAULT_RPS_ALLOWED_EXTENSIONS = "pdf"
DEFAULT_RPS_CONVERTER = "docling"
DEFAULT_RPS_CONVERTER_OCR = True
DEFAULT_RPS_CONVERTER_TABLE_STRUCTURE = True
DEFAULT_RPS_CONVERTER_TABLE_MODE = "accurate"
# Batas waktu pemrosesan yang masih dianggap berjalan. Setelah ini, dokumen
# berstatus PROCESSING boleh diproses ulang — jalan keluar bila proses server
# berhenti di tengah konversi sehingga barisnya tidak pernah selesai.
DEFAULT_RPS_PROCESSING_LEASE_SECONDS = 900

# Batas panjang Additional Prompt dosen (BE-10.2). Prompt ini ikut dikirim ke
# LLM bersama konteks RPS, sehingga panjangnya dibatasi agar konteks akademik
# tidak tergeser oleh instruksi tambahan.
DEFAULT_INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH = 2000


class Settings(BaseSettings):
    APP_NAME: str
    APP_ENV: str
    DEBUG: bool
    HOST: str
    PORT: int

    SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DATABASE_URL: str = ""

    CORS_ORIGINS: Union[List[str], str]

    MOODLE_BASE_URL: str
    MOODLE_WEB_SERVICE_TOKEN: str

    LLM_PROVIDER: str
    # Optional shared credential/model, kept for single-provider setups. Prefer
    # the provider-specific values below: a shared value only applies to the
    # provider selected by LLM_PROVIDER, so it can never be sent to the other
    # provider by accident.
    LLM_API_KEY: str = ""
    LLM_MODEL: str = ""

    # Provider-specific LLM credentials and models. An empty value means "not
    # set": the provider then falls back to LLM_API_KEY / LLM_MODEL above when
    # it is the provider selected by LLM_PROVIDER, and to its own provisional
    # default model otherwise. These credentials are backend-only: they must
    # never be returned to the frontend nor handed to agent code directly (see
    # services/llm/).
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = ""

    # Optional OpenAI-compatible endpoint override, e.g. a local runtime such as
    # Ollama (http://localhost:11434/v1). Empty means the official OpenAI API.
    OPENAI_BASE_URL: str = ""

    # --- RPS upload & Docling conversion (BE-05) ---------------------------
    # Seluruh nilai default-nya kosong; nilai bawaan diterapkan oleh property
    # ``rps_*`` di bawah (lihat DEFAULT_RPS_* pada modul ini). Kosong berarti
    # "tidak dikonfigurasi", bukan "nonaktif".
    #
    # Direktori penyimpanan dokumen RPS; kosong berarti DEFAULT_RPS_STORAGE_DIR
    # (backend/var/rps). Isi folder ini tidak masuk repository.
    RPS_STORAGE_DIR: str = ""
    # Batas ukuran berkas RPS yang diterima (byte). RPS berupa dokumen teks, dan
    # batas ini melindungi server dari unggahan tak wajar.
    RPS_MAX_UPLOAD_BYTES: int | None = None
    # Ekstensi yang diterima, dipisah koma. Bawaannya hanya PDF sesuai cakupan
    # M02 (issue BE-05); design-api §6.1 juga mengizinkan DOCX, yang dapat
    # diaktifkan lewat konfigurasi tanpa mengubah kode.
    RPS_ALLOWED_EXTENSIONS: str = ""
    # Nama konverter dokumen; lihat src/services/rps/factory.py.
    RPS_CONVERTER: str = ""
    # OCR untuk halaman tanpa lapisan teks (RPS hasil pindai). Bawaannya aktif
    # mengikuti default Docling; menonaktifkannya mempercepat PDF digital.
    RPS_CONVERTER_OCR: bool | None = None
    # Ekstraksi struktur tabel. Bawaannya aktif: tabel RPS (distribusi mingguan,
    # bobot penilaian) adalah data akademik yang tidak boleh hilang.
    RPS_CONVERTER_TABLE_STRUCTURE: bool | None = None
    # "accurate" atau "fast" (mode TableFormer Docling).
    RPS_CONVERTER_TABLE_MODE: str = ""
    # Direktori model Docling yang sudah diunduh lebih dulu (deployment offline).
    RPS_CONVERTER_ARTIFACTS_PATH: str = ""
    # Batas waktu (detik) sebuah pemrosesan dianggap masih berjalan. Dokumen
    # berstatus PROCESSING yang lebih tua dari ini boleh diproses ulang, sehingga
    # konversi yang terputus (server dimatikan) tidak mengunci dokumen selamanya.
    RPS_PROCESSING_LEASE_SECONDS: int | None = None

    # --- Instructor Setup (BE-10.2) ---------------------------------------
    # Batas panjang Additional Prompt (karakter). Kosong berarti nilai bawaan
    # DEFAULT_INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH.
    INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH: int | None = None

    model_config = SettingsConfigDict(
        # Urutan penting: pydantic-settings menggabungkan file-file ini secara
        # berurutan dan file TERAKHIR yang menang. ``.env.example`` diletakkan
        # paling awal karena hanya berfungsi sebagai fallback agar checkout
        # baru (dan CI) tetap dapat menjalankan aplikasi/test tanpa ``.env``
        # privat; konfigurasi milik developer (``.env``) harus selalu
        # menimpanya.
        env_file=(
            BACKEND_DIR / ".env.example",
            ROOT_DIR / ".env",
            BACKEND_DIR / ".env",
        ),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Normalisasi daftar origin frontend yang diizinkan (BE-06.2).

        Menerima JSON array (``["http://localhost:3000"]``) maupun daftar yang
        dipisah koma. Setiap origin divalidasi dan dinormalisasi (tanpa spasi di
        tepi, tanpa garis miring di akhir, huruf kecil) supaya cocok persis
        dengan nilai header ``Origin`` yang dikirim browser. Konfigurasi yang
        salah gagal saat startup, bukan ketika browser pertama kali mengirim
        preflight.
        """
        return _normalize_cors_origins(v)

    @field_validator("RPS_CONVERTER_TABLE_MODE", mode="after")
    @classmethod
    def parse_rps_table_mode(cls, v: str) -> str:
        """Mode tabel tidak dikenal gagal saat startup, bukan saat request pertama."""
        mode = (v or "").strip().lower()
        if mode and mode not in RPS_TABLE_MODES:
            raise ValueError(
                f"RPS_CONVERTER_TABLE_MODE harus salah satu dari: {', '.join(RPS_TABLE_MODES)}"
            )
        return mode

    @field_validator("RPS_MAX_UPLOAD_BYTES", mode="after")
    @classmethod
    def parse_rps_max_upload_bytes(cls, v: int | None) -> int | None:
        """Batas 0 atau negatif akan menolak seluruh unggahan tanpa penjelasan jelas."""
        if v is not None and v <= 0:
            raise ValueError("RPS_MAX_UPLOAD_BYTES harus lebih besar dari 0")
        return v

    @field_validator("RPS_PROCESSING_LEASE_SECONDS", mode="after")
    @classmethod
    def parse_rps_processing_lease(cls, v: int | None) -> int | None:
        """Lease 0/negatif akan menganggap setiap pemrosesan sudah terlantar."""
        if v is not None and v <= 0:
            raise ValueError("RPS_PROCESSING_LEASE_SECONDS harus lebih besar dari 0")
        return v

    @field_validator("RPS_ALLOWED_EXTENSIONS", mode="after")
    @classmethod
    def parse_rps_allowed_extensions(cls, v: str) -> str:
        """Daftar berisi pemisah saja (mis. ``",,"``) adalah salah konfigurasi."""
        if (v or "").strip() and not _split_extensions(v):
            raise ValueError(
                "RPS_ALLOWED_EXTENSIONS tidak boleh kosong; contoh: pdf atau pdf,docx"
            )
        return v

    @field_validator("INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH", mode="after")
    @classmethod
    def parse_instructor_prompt_max_length(cls, v: int | None) -> int | None:
        """Batas 0/negatif akan menolak setiap prompt tanpa penjelasan jelas."""
        if v is not None and v <= 0:
            raise ValueError(
                "INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH harus lebih besar dari 0"
            )
        return v

    @property
    def rps_storage_path(self) -> Path:
        """Direktori absolut penyimpanan dokumen RPS."""
        raw = (self.RPS_STORAGE_DIR or "").strip()
        return Path(raw).expanduser() if raw else DEFAULT_RPS_STORAGE_DIR

    @property
    def rps_max_upload_bytes(self) -> int:
        """Batas ukuran unggahan yang berlaku (byte)."""
        return (
            DEFAULT_RPS_MAX_UPLOAD_BYTES
            if self.RPS_MAX_UPLOAD_BYTES is None
            else self.RPS_MAX_UPLOAD_BYTES
        )

    @property
    def rps_allowed_extensions(self) -> tuple[str, ...]:
        """Ekstensi yang diterima, huruf kecil tanpa titik."""
        return _split_extensions(self.RPS_ALLOWED_EXTENSIONS) or (
            DEFAULT_RPS_ALLOWED_EXTENSIONS,
        )

    @property
    def rps_converter(self) -> str:
        """Nama konverter dokumen yang aktif."""
        return (self.RPS_CONVERTER or "").strip().lower() or DEFAULT_RPS_CONVERTER

    @property
    def rps_converter_ocr(self) -> bool:
        """Apakah OCR dijalankan untuk halaman tanpa lapisan teks."""
        return (
            DEFAULT_RPS_CONVERTER_OCR
            if self.RPS_CONVERTER_OCR is None
            else self.RPS_CONVERTER_OCR
        )

    @property
    def rps_converter_table_structure(self) -> bool:
        """Apakah struktur tabel diekstrak."""
        return (
            DEFAULT_RPS_CONVERTER_TABLE_STRUCTURE
            if self.RPS_CONVERTER_TABLE_STRUCTURE is None
            else self.RPS_CONVERTER_TABLE_STRUCTURE
        )

    @property
    def rps_converter_table_mode(self) -> str:
        """Mode TableFormer yang berlaku."""
        return (self.RPS_CONVERTER_TABLE_MODE or "").strip().lower() or (
            DEFAULT_RPS_CONVERTER_TABLE_MODE
        )

    @property
    def rps_converter_artifacts_path(self) -> str | None:
        """Direktori model Docling, atau ``None`` bila memakai cache bawaan."""
        return (self.RPS_CONVERTER_ARTIFACTS_PATH or "").strip() or None

    @property
    def rps_processing_lease_seconds(self) -> int:
        """Batas waktu pemrosesan yang dianggap masih berjalan (detik)."""
        return (
            DEFAULT_RPS_PROCESSING_LEASE_SECONDS
            if self.RPS_PROCESSING_LEASE_SECONDS is None
            else self.RPS_PROCESSING_LEASE_SECONDS
        )

    @property
    def instructor_additional_prompt_max_length(self) -> int:
        """Batas panjang Additional Prompt yang berlaku (karakter)."""
        return (
            DEFAULT_INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH
            if self.INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH is None
            else self.INSTRUCTOR_ADDITIONAL_PROMPT_MAX_LENGTH
        )

    @property
    def llm_provider(self) -> str:
        """Canonical name of the provider selected through LLM_PROVIDER."""
        name = (self.LLM_PROVIDER or "").strip().lower()
        return LLM_PROVIDER_ALIASES.get(name, name)

    def _llm_setting_for(self, provider: str, suffix: str) -> str:
        """Provider-specific value, else the shared value for the active provider.

        The shared LLM_API_KEY / LLM_MODEL values describe the provider chosen
        by LLM_PROVIDER. They are deliberately NOT reused for the other
        provider, so an OpenAI credential or model name can never be sent to
        Gemini (or the other way around) by accident.
        """
        own_value = getattr(self, f"{provider.upper()}_{suffix}", "")
        if own_value:
            return own_value
        if self.llm_provider == provider.lower():
            return getattr(self, f"LLM_{suffix}", "")
        return ""

    def llm_api_key_for(self, provider: str) -> str:
        """Resolve the credential of a provider (empty when not configured)."""
        return self._llm_setting_for(provider, "API_KEY")

    def llm_model_for(self, provider: str) -> str:
        """Resolve the model of a provider (empty when not configured)."""
        return self._llm_setting_for(provider, "MODEL")

    @property
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def _split_extensions(value: str) -> tuple[str, ...]:
    """Ubah ``"pdf, .DOCX"`` menjadi ``("pdf", "docx")``."""
    parts = (part.strip().lower().lstrip(".") for part in (value or "").split(","))
    return tuple(part for part in parts if part)


def _normalize_cors_origins(value: Union[str, List[str]]) -> List[str]:
    """Ubah konfigurasi CORS menjadi daftar origin kanonik tanpa duplikat.

    ``CORS_ORIGINS`` boleh berupa JSON array atau string dipisah koma. Origin
    harus eksplisit (``scheme://host[:port]``); wildcard dan URL dengan path
    ditolak, sehingga "origin yang tidak terdaftar ditolak" tetap dapat
    dibuktikan dan tidak ada konfigurasi development yang terbawa ke produksi
    secara tidak sengaja.
    """
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "CORS_ORIGINS harus berupa JSON array yang valid atau daftar "
                    "origin yang dipisah koma"
                ) from exc
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON harus berupa array string")
            items: list[object] = parsed
        else:
            items = raw.split(",")
    else:
        items = list(value)

    origins: List[str] = []
    for item in items:
        if not isinstance(item, str):
            raise ValueError("Setiap CORS origin harus berupa string")
        origin = _normalize_cors_origin(item)
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def _normalize_cors_origin(value: str) -> str:
    """Validasi satu origin dan kembalikan bentuk kanoniknya.

    Nilai kosong diabaikan (mis. sisa koma pada daftar). Origin kosong secara
    total tetap diperbolehkan: artinya tidak ada frontend yang diizinkan, bukan
    "izinkan semua".
    """
    candidate = value.strip()
    if not candidate:
        return ""
    if candidate == "*":
        raise ValueError(
            "CORS_ORIGINS tidak boleh memakai wildcard '*'; daftarkan origin "
            "frontend secara eksplisit"
        )

    normalized = candidate.rstrip("/")
    parts = urlsplit(normalized)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        raise ValueError(
            f"CORS origin tidak valid: {candidate!r}; gunakan format "
            "scheme://host[:port], contoh http://localhost:3000"
        )
    if parts.path or parts.query or parts.fragment:
        raise ValueError(
            f"CORS origin tidak boleh memuat path/query/fragment: {candidate!r}"
        )
    if parts.username or parts.password:
        raise ValueError(f"CORS origin tidak boleh memuat credential: {candidate!r}")
    try:
        # Port yang tidak valid (mis. ":abc") baru terdeteksi saat diakses.
        parts.port
    except ValueError as exc:
        raise ValueError(f"CORS origin memuat port tidak valid: {candidate!r}") from exc

    # Browser mengirim scheme dan host dalam huruf kecil; normalisasi yang sama
    # membuat pencocokan di middleware bersifat persis (exact match).
    return f"{parts.scheme.lower()}://{parts.netloc.lower()}"


settings = get_settings()
