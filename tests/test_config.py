import pytest
from pydantic import ValidationError

from packages.core.config import Settings


def test_production_requires_api_key() -> None:
    with pytest.raises(ValidationError, match="EFI_API_KEY"):
        Settings(
            environment="production",
            database_url="postgresql+psycopg://efi:secret@db/efi_ai",
        )


def test_production_requires_postgresql() -> None:
    with pytest.raises(ValidationError, match="PostgreSQL"):
        Settings(
            environment="production",
            api_key="test-key",
            database_url="sqlite:///./test.db",
        )


def test_production_cannot_disable_paper_trading() -> None:
    with pytest.raises(ValidationError, match="EFI_PAPER_TRADING"):
        Settings(
            environment="production",
            api_key="test-key",
            database_url="postgresql+psycopg://efi:secret@db/efi_ai",
            paper_trading=False,
        )


def test_production_safe_configuration_is_valid() -> None:
    settings = Settings(
        environment="production",
        api_key="test-key",
        database_url="postgresql+psycopg://efi:secret@db/efi_ai",
    )
    assert settings.paper_trading is True


def test_cloud_database_url_alias_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://efi:secret@db/efi_ai")
    settings = Settings(environment="production", api_key="test-key")
    assert settings.database_url.startswith("postgresql")


def test_databento_key_alias_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABENTO_API_KEY", "db-test-key")
    settings = Settings()
    assert settings.databento_api_key == "db-test-key"
    assert settings.has_databento_credentials is True
