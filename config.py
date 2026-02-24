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

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()

