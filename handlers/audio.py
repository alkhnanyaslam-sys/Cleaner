"""
handlers/audio.py
Core flow: receive audio/video/voice -> validate -> queue -> separate -> deliver.
"""
import os
import uuid

from aiogram import Router, F, Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, CallbackQuery, FSInputFile

from config import config
from database import db
from keyboards.main import result_kb
from services import ffmpeg as ffmpeg_service
from services.downloader import download_telegram_file
from services.queue_manager import queue_manager
from services.separation import separate
from services.cleanup import delete_path
from utils.logger import logger
from utils.validators import is_supported_extension, is_video_extension, is_within_size_limit

router = Router(name="audio")

# job_id -> {"vocals": path, "instrumental": path, "dir": path}
_job_results: dict = {}


async def _safe_edit(message: Message, text: str):
    """Edits a message's text, silently ignoring Telegram's
    'message is not modified' error when the text hasn't actually changed."""
    try:
        await message.edit_text(text)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise


def _get_file_meta(message: Message):
    """Extracts (file_id, file_name, file_size) from any supported message type."""
    if message.audio:
        return message.audio.file_id, message.audio.file_name or "audio.mp3", message.audio.file_size
    if message.voice:
        return message.voice.file_id, "voice.ogg", message.voice.file_size
    if message.video:
        return message.video.file_id, message.video.file_name or "video.mp4", message.video.file_size
    if message.document:
        return message.document.file_id, message.document.file_name or "file.bin", message.document.file_size
    return None, None, None


@router.message(F.audio | F.voice | F.video | F.document)
async def handle_media(message: Message, bot: Bot):
    user_id = message.from_user.id

    if await db.is_banned(user_id):
        await message.answer("🚫 تم حظرك من استخدام هذا البوت.")
        return

    file_id, file_name, file_size = _get_file_meta(message)
    if not file_id:
        return

    if not is_supported_extension(file_name):
        await message.answer("⚠️ نوع الملف غير مدعوم. ابعت ملف صوتي أو فيديو.")
        return

    if file_size and not is_within_size_limit(file_size, config.MAX_FILE_SIZE_BYTES):
        await message.answer(f"⚠️ حجم الملف أكبر من الحد المسموح ({config.MAX_FILE_SIZE_MB}MB).")
        return

    if queue_manager.user_active_count(user_id) >= config.MAX_CONCURRENT_PER_USER:
        await message.answer("⏳ عندك ملف قيد المعالجة بالفعل، استنى لحد ما يخلص.")
        return

    jobs_today = await db.count_jobs_today(user_id)
    if jobs_today >= config.MAX_JOBS_PER_USER_DAILY:
        await message.answer("🚫 وصلت للحد الأقصى من العمليات المسموحة اليوم.")
        return

    await db.upsert_user(user_id, message.from_user.username, message.from_user.first_name)

    status_msg = await message.answer("⏳ جاري الانتظار في الطابور...")

    job_id = uuid.uuid4().hex[:12]
    await db.create_job(job_id, user_id)

    async def status_callback(status: str):
        # Only handle the "failed" case here; the "processing" text is set
        # directly inside _process_job to avoid a duplicate identical edit.
        if status == "failed":
            await _safe_edit(status_msg, "❌ حدث خطأ أثناء المعالجة. حاول لاحقًا.")

    async def job_coro():
        await _process_job(bot, message, job_id, file_id, file_name, status_msg)

    await queue_manager.submit(user_id, job_coro, status_callback)
    queue_manager.start_workers()


async def _process_job(bot: Bot, message: Message, job_id: str, file_id: str,
                        file_name: str, status_msg: Message):
    job_dir = os.path.join(config.TEMP_DIR, job_id)
    os.makedirs(job_dir, exist_ok=True)

    try:
        await _safe_edit(status_msg, "⚙️ جاري تحليل الصوت...")

        raw_path = await download_telegram_file(bot, file_id, file_name, job_dir)

        wav_input = os.path.join(job_dir, "input.wav")
        if is_video_extension(file_name):
            await ffmpeg_service.extract_audio_from_video(raw_path, wav_input)
        else:
            await ffmpeg_service.normalize_input_audio(raw_path, wav_input)

        duration = await ffmpeg_service.probe_duration(wav_input)
        if duration > config.MAX_DURATION_SECONDS:
            await _safe_edit(
                status_msg,
                f"⚠️ مدة الملف ({int(duration // 60)} دقيقة) أكبر من الحد المسموح "
                f"({config.MAX_DURATION_SECONDS // 60} دقيقة)."
            )
            await db.finish_job(job_id, success=False, error="duration_exceeded")
            delete_path(job_dir)
            return

        await _safe_edit(status_msg, "🎛️ جاري فصل الصوت...")

        vocals_path, instrumental_path, processing_time = await separate(
            wav_input, job_dir, config.MODEL_NAME
        )

        await _safe_edit(status_msg, "📤 جاري رفع النتيجة...")

        _job_results[job_id] = {
            "vocals": vocals_path,
            "instrumental": instrumental_path,
            "dir": job_dir,
        }

        await _safe_edit(status_msg, "✅ اكتملت المعالجة.")
        await message.answer(
            "🎉 تم فصل الصوت بنجاح! اختار إيه اللي عايز تحمله:",
            reply_markup=result_kb(job_id),
        )

        await db.finish_job(job_id, success=True, duration_seconds=duration,
                             processing_time_seconds=processing_time)

    except Exception:
        logger.exception(f"Job {job_id} processing failed")
        await _safe_edit(status_msg, "❌ حدث خطأ أثناء المعالجة. حاول بملف آخر أو لاحقًا.")
        await db.finish_job(job_id, success=False, error="processing_error")
        delete_path(job_dir)


@router.callback_query(F.data.startswith("result:"))
async def handle_result_choice(callback: CallbackQuery):
    parts = callback.data.split(":")
    action = parts[1]
    if action == "new":
        return  # handled in handlers/start.py

    job_id = parts[2]
    result = _job_results.get(job_id)
    if not result:
        await callback.answer("⚠️ النتيجة لم تعد متاحة، ابعت الملف تاني.", show_alert=True)
        return

    await callback.answer("📤 جاري الإرسال...")

    if action in ("vocal", "both"):
        await callback.message.answer_audio(
            FSInputFile(result["vocals"]), caption="🎤 الصوت (Vocal)"
        )
    if action in ("music", "both"):
        await callback.message.answer_audio(
            FSInputFile(result["instrumental"]), caption="🎵 الموسيقى (Instrumental)"
        )

    # Delete the result files immediately after successful delivery (privacy).
    delete_path(result["dir"])
    _job_results.pop(job_id, None)
