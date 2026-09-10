from pathlib import Path
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
