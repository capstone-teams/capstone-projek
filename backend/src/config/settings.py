import json
from functools import lru_cache
from pathlib import Path
from typing import List, Union

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
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

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

    @field_validator("RPS_ALLOWED_EXTENSIONS", mode="after")
    @classmethod
    def parse_rps_allowed_extensions(cls, v: str) -> str:
        """Daftar berisi pemisah saja (mis. ``",,"``) adalah salah konfigurasi."""
        if (v or "").strip() and not _split_extensions(v):
            raise ValueError(
                "RPS_ALLOWED_EXTENSIONS tidak boleh kosong; contoh: pdf atau pdf,docx"
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


settings = get_settings()
