from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    rate_limit_delay: float = Field(1.0, validation_alias="RATE_LIMIT_DELAY")
    request_timeout: float = Field(10.0, validation_alias="REQUEST_TIMEOUT")
    max_retries: int = Field(3, validation_alias="MAX_RETRIES")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", validation_alias="LOG_LEVEL"
    )
    port: int = Field(8000, validation_alias="PORT")
    greenhouse_companies: str = Field(
        "",
        validation_alias="GREENHOUSE_COMPANIES",
        description="Comma-separated Greenhouse board tokens to search across.",
    )
    lever_companies: str = Field(
        "",
        validation_alias="LEVER_COMPANIES",
        description="Comma-separated Lever site names to search across.",
    )
    search_max_companies: int = Field(
        50,
        validation_alias="SEARCH_MAX_COMPANIES",
        description="Safety cap on how many companies are scraped in /search.",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

