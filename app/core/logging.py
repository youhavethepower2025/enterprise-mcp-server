import logging
from logging.config import dictConfig

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the API + tool executions."""

    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                }
            },
            "root": {
                "level": settings.log_level,
                "handlers": ["console"],
            },
        }
    )


setup_logging()
