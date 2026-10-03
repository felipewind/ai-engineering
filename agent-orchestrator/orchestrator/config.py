"""Loads settings from the .env file."""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when a required setting is missing."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str


def get_settings() -> Settings:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key == "your-openai-api-key-here":
        logger.error("OPENAI_API_KEY is not set")
        raise ConfigError(
            "OPENAI_API_KEY is not set. Copy .env.example to .env and fill in your key."
        )

    settings = Settings(
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "").strip() or "gpt-4o-mini",
    )
    # Never log the API key.
    logger.debug("settings loaded model=%s", settings.openai_model)
    return settings
