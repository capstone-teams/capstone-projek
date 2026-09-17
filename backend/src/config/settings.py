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

    model_config = SettingsConfigDict(
        env_file=(
            ROOT_DIR / ".env",
            BACKEND_DIR / ".env",
            BACKEND_DIR / ".env.example",
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


settings = get_settings()
