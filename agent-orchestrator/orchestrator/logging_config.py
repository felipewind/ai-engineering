"""Configures logging from the LOG_LEVEL setting in the .env file."""

import logging
import os

from dotenv import load_dotenv

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
DATE_FORMAT = "%H:%M:%S"
PROJECT_LOGGERS = ("orchestrator", "app")
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

_configured = False


def setup_logging() -> None:
    global _configured
    # Streamlit reruns app.py on every interaction: configure only once.
    if _configured:
        return
    _configured = True

    load_dotenv()
    level_name = os.getenv("LOG_LEVEL", "").strip().upper() or "INFO"
    invalid = level_name not in VALID_LEVELS
    if invalid:
        bad_value, level_name = level_name, "INFO"

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root = logging.getLogger()
    root.addHandler(handler)
    # Third-party libraries (httpx, openai, ...) only show warnings and errors.
    root.setLevel(logging.WARNING)

    for name in PROJECT_LOGGERS:
        logging.getLogger(name).setLevel(level_name)

    logger = logging.getLogger(__name__)
    if invalid:
        logger.warning("invalid LOG_LEVEL=%r, using INFO", bad_value)
    logger.info("logging configured level=%s", level_name)
