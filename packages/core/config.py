from functools import lru_cache

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "EFI-AI"
    environment: str = "development"
    log_level: str = "INFO"
    paper_trading: bool = True
    api_key: str = ""
    database_url: str = Field(
        default="sqlite:///./efi_ai.db",
        validation_alias=AliasChoices("EFI_DATABASE_URL", "DATABASE_URL"),
    )
    max_position_notional: float = 10_000.0
    max_daily_loss: float = 1_000.0
    alpaca_api_key_id: str = Field(
        default="",
        validation_alias=AliasChoices("APCA_API_KEY_ID", "EFI_ALPACA_API_KEY_ID"),
    )
    alpaca_api_secret_key: str = Field(
        default="",
        validation_alias=AliasChoices("APCA_API_SECRET_KEY", "EFI_ALPACA_API_SECRET_KEY"),
    )
    alpaca_options_feed: str = Field(
        default="indicative",
        validation_alias=AliasChoices("APCA_OPTIONS_FEED", "EFI_ALPACA_OPTIONS_FEED"),
    )

    model_config = SettingsConfigDict(env_prefix="EFI_", env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def enforce_production_safety(self) -> "Settings":
        if self.alpaca_options_feed not in {"indicative", "opra"}:
            raise ValueError("APCA_OPTIONS_FEED must be either 'indicative' or 'opra'")
        if self.environment.lower() == "production":
            if not self.paper_trading:
                raise ValueError("EFI_PAPER_TRADING must remain true in production until live execution is explicitly approved")
            if not self.api_key:
                raise ValueError("EFI_API_KEY is required in production")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("EFI_DATABASE_URL/DATABASE_URL must use PostgreSQL in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
