"""
services/ffmpeg.py
Safe wrappers around ffmpeg / ffprobe. Never builds a shell string from
user input -- always uses argument lists with subprocess, no shell=True.
"""
import asyncio
import json
import os

from utils.logger import logger


class FFmpegError(Exception):
    pass


async def _run(cmd: list) -> tuple:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return proc.returncode, stdout, stderr


async def probe_duration(filepath: str) -> float:
    """Returns duration in seconds using ffprobe. Raises FFmpegError on failure."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        filepath,
    ]
    code, stdout, stderr = await _run(cmd)
    if code != 0:
        logger.error("ffprobe failed for a job (details omitted)")
        raise FFmpegError("تعذر قراءة معلومات الملف")
    try:
        data = json.loads(stdout.decode("utf-8", errors="ignore"))
        return float(data["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError):
        raise FFmpegError("الملف تالف أو غير مدعوم")


async def extract_audio_from_video(video_path: str, output_wav_path: str) -> None:
    """Extracts audio track from a video file into a WAV file."""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
        output_wav_path,
    ]
    code, stdout, stderr = await _run(cmd)
    if code != 0:
        logger.error("ffmpeg extract_audio failed for a job")
        raise FFmpegError("فشل استخراج الصوت من الفيديو")


async def convert_to_mp3(wav_path: str, mp3_path: str, bitrate: str = "256k") -> None:
    cmd = [
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-b:a", bitrate,
        mp3_path,
    ]
    code, stdout, stderr = await _run(cmd)
    if code != 0:
        logger.error("ffmpeg convert_to_mp3 failed for a job")
        raise FFmpegError("فشل تحويل الملف الناتج")


async def normalize_input_audio(input_path: str, output_wav_path: str) -> None:
    """Converts any supported audio input into a standard WAV for Demucs."""
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-ar", "44100", "-ac", "2",
        output_wav_path,
    ]
    code, stdout, stderr = await _run(cmd)
    if code != 0:
        logger.error("ffmpeg normalize_input_audio failed for a job")
        raise FFmpegError("فشل تجهيز الملف الصوتي")
