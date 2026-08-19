"""
services/cleanup.py
Background worker that deletes temp files older than RESULT_TTL_MINUTES,
and helper to wipe a specific job's files immediately after delivery.
"""
import asyncio
import os
import shutil
import time

from config import config
from utils.logger import logger


def delete_path(path: str) -> None:
    try:
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass


async def cleanup_loop(interval_seconds: int = 300):
    """Runs forever, periodically removing expired temp files."""
    while True:
        try:
            _sweep_temp_dir()
        except Exception:
            logger.exception("Cleanup sweep failed")
        await asyncio.sleep(interval_seconds)


def _sweep_temp_dir():
    if not os.path.isdir(config.TEMP_DIR):
        return
    ttl_seconds = config.RESULT_TTL_MINUTES * 60
    now = time.time()
    for name in os.listdir(config.TEMP_DIR):
        full_path = os.path.join(config.TEMP_DIR, name)
        try:
            age = now - os.path.getmtime(full_path)
            if age > ttl_seconds:
                delete_path(full_path)
                logger.info("Removed expired temp job directory")
        except OSError:
            continue
