"""
services/downloader.py
Safely downloads a Telegram file (audio/video/voice) to a temp path.
"""
import os

from aiogram import Bot

from utils.logger import logger
from utils.validators import safe_filename


async def download_telegram_file(bot: Bot, file_id: str, original_name: str, dest_dir: str) -> str:
    os.makedirs(dest_dir, exist_ok=True)
    filename = safe_filename(original_name or "file.bin")
    dest_path = os.path.join(dest_dir, filename)

    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, destination=dest_path)

    logger.info(f"Downloaded file for job (size hidden), saved to isolated temp path")
    return dest_path
