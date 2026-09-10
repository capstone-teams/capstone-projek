import json
from functools import lru_cache
from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ROOT_DIR = BACKEND_DIR.parent


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
    LLM_API_KEY: str
    LLM_MODEL: str

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
    def async_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
