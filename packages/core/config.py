from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EFI-AI"
    environment: str = "development"
    log_level: str = "INFO"
    paper_trading: bool = True
    api_key: str = ""
    database_url: str = "sqlite:///./efi_ai.db"
    max_position_notional: float = 10_000.0
    max_daily_loss: float = 1_000.0

    model_config = SettingsConfigDict(env_prefix="EFI_", env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
