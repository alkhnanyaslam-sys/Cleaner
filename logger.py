"""
utils/logger.py
Central logger. Never logs raw file paths of user audio or user personal
data content -- only IDs and event types, to respect user privacy.
"""
import logging
import os
import sys

os.makedirs("logs", exist_ok=True)

logger = logging.getLogger("audio_bot")
logger.setLevel(logging.INFO)

_fmt = logging.Formatter(
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_file_handler = logging.FileHandler("logs/bot.log", encoding="utf-8")
_file_handler.setFormatter(_fmt)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setFormatter(_fmt)

if not logger.handlers:
    logger.addHandler(_file_handler)
    logger.addHandler(_console_handler)
