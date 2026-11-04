from pathlib import Path

import pytest
from pydantic import ValidationError
from pydantic_core import PydanticUndefined

from src.config.settings import Settings, get_settings

ENV_PATH = Path(__file__).parent.parent / ".env"
ENV_EXAMPLE_PATH = Path(__file__).parent.parent / ".env.example"


def test_load_settings():
    env_file = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    settings = Settings(_env_file=str(env_file))
    assert settings.APP_NAME
    assert settings.APP_ENV
    assert settings.PORT
    assert "postgresql+asyncpg://" in settings.async_database_url


def test_env_override(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PORT", "9000")
    monkeypatch.setenv("SECRET_KEY", "custom_prod_secret_key_123456789")
    monkeypatch.setenv("DB_NAME", "prod_db")

    settings = Settings()
    assert settings.APP_ENV == "production"
    assert settings.PORT == 9000
    assert settings.SECRET_KEY == "custom_prod_secret_key_123456789"
    assert settings.DB_NAME == "prod_db"
    assert "prod_db" in settings.async_database_url


def test_cors_origins_parsing(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://example.com, https://app.example.com")
    settings = Settings()
    assert settings.CORS_ORIGINS == ["http://example.com", "https://app.example.com"]

    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:3000", "http://127.0.0.1:3000"]')
    settings = Settings()
    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_cors_origins_are_normalized_for_exact_origin_matching(monkeypatch):
    """Browser mengirim origin lowercase tanpa trailing slash."""
    monkeypatch.setenv(
        "CORS_ORIGINS",
        " HTTP://LOCALHOST:3000/ , http://localhost:3000 , http://127.0.0.1:3000/ ",
    )

    settings = Settings()

    assert settings.CORS_ORIGINS == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_empty_cors_origins_means_no_frontend_is_allowed(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "  ")

    assert Settings().CORS_ORIGINS == []


@pytest.mark.parametrize(
    "value",
    [
        "*",
        "http://localhost:3000/api",
        "localhost:3000",
        "ftp://localhost:3000",
        "http://localhost:abc",
        '["http://localhost:3000"',
        '{"origin": "http://localhost:3000"}',
    ],
    ids=[
        "wildcard",
        "path",
        "missing-scheme",
        "unsupported-scheme",
        "invalid-port",
        "invalid-json",
        "not-an-array",
    ],
)
def test_invalid_cors_configuration_fails_at_startup(monkeypatch, value):
    """Konfigurasi salah harus gagal saat startup, bukan saat preflight pertama."""
    monkeypatch.setenv("CORS_ORIGINS", value)

    with pytest.raises(ValidationError):
        Settings()


def test_env_keys_match_settings():
    env_file = ENV_PATH if ENV_PATH.exists() else ENV_EXAMPLE_PATH
    content = env_file.read_text()
    keys_in_env = {
        line.split("=", 1)[0].strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#") and "=" in line
    }
    settings_fields = set(Settings.model_fields.keys())
    assert keys_in_env.issubset(settings_fields)


def test_secrets_not_hardcoded_in_settings():
    for field_name, field_info in Settings.model_fields.items():
        assert field_info.default in (PydanticUndefined, "", None) or field_name == "DATABASE_URL"


def test_get_settings_caching():
    assert get_settings() is get_settings()


def test_env_example_is_the_lowest_priority_env_file():
    """Konfigurasi milik developer harus menang atas ``.env.example``.

    pydantic-settings menggabungkan ``env_file`` secara berurutan dan file
    terakhir yang menang. Bila ``.env.example`` tidak berada di urutan pertama,
    nilai placeholder yang ter-commit (SECRET_KEY, DB_PASSWORD, token Moodle,
    dsb.) akan menimpa ``.env`` lokal.
    """
    env_file_names = [Path(path).name for path in Settings.model_config["env_file"]]

    assert env_file_names == [".env.example", ".env", ".env"]
