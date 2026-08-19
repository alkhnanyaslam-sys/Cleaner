"""
config.py
Loads all configuration from environment variables (.env).
Nothing is hard-coded — every limit/setting comes from here.
"""
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_admin_ids() -> List[int]:
    raw = os.getenv("ADMIN_IDS", "")
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


@dataclass
class Config:
    # Telegram
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    ADMIN_IDS: List[int] = field(default_factory=_get_admin_ids)

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "database/bot.db")

    # Limits (all configurable, can be overridden at runtime by admin panel)
    MAX_FILE_SIZE_MB: int = _get_int("MAX_FILE_SIZE_MB", 50)
    MAX_DURATION_SECONDS: int = _get_int("MAX_DURATION_SECONDS", 600)
    MAX_WORKERS: int = _get_int("MAX_WORKERS", 1)
    MAX_CONCURRENT_PER_USER: int = _get_int("MAX_CONCURRENT_PER_USER", 1)
    MAX_JOBS_PER_USER_DAILY: int = _get_int("MAX_JOBS_PER_USER_DAILY", 10)

    # AI model
    MODEL_NAME: str = os.getenv("MODEL_NAME", "htdemucs")

    # Storage
    TEMP_DIR: str = os.getenv("TEMP_DIR", "temp")
    RESULT_TTL_MINUTES: int = _get_int("RESULT_TTL_MINUTES", 30)

    # Runtime (used for the GitHub Actions 6h-restart strategy)
    RUN_DURATION_MINUTES: int = _get_int("RUN_DURATION_MINUTES", 350)

    @property
    def MAX_FILE_SIZE_BYTES(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


config = Config()

if not config.BOT_TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Create a .env file based on .env.example "
        "or set it as an environment variable / GitHub secret."
    )
