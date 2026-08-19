"""
utils/validators.py
Validates incoming files before any processing happens.
"""
import os
import re
import uuid

ALLOWED_AUDIO_EXT = {".mp3", ".wav", ".ogg", ".m4a", ".flac", ".oga"}
ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm"}
ALLOWED_EXT = ALLOWED_AUDIO_EXT | ALLOWED_VIDEO_EXT


def is_supported_extension(filename: str) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in ALLOWED_EXT


def is_video_extension(filename: str) -> bool:
    ext = os.path.splitext(filename or "")[1].lower()
    return ext in ALLOWED_VIDEO_EXT


def safe_filename(original: str) -> str:
    """
    Generates a random, isolated filename so user input never controls
    a path that is passed to the filesystem or a subprocess.
    """
    ext = os.path.splitext(original or "")[1].lower()
    ext = re.sub(r"[^a-z0-9.]", "", ext)[:10] or ".bin"
    return f"{uuid.uuid4().hex}{ext}"


def is_within_size_limit(size_bytes: int, max_bytes: int) -> bool:
    return 0 < size_bytes <= max_bytes


def is_within_duration_limit(duration_seconds: float, max_seconds: int) -> bool:
    return 0 < duration_seconds <= max_seconds
