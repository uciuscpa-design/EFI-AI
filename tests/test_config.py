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
