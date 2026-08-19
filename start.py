"""
handlers/start.py
/start, help and main-menu callback handlers.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database import db
from keyboards.main import main_menu_kb

router = Router(name="start")

WELCOME_TEXT = (
    "🎧 أهلاً بك في بوت فصل الصوت\n"
    "أرسل أغنية (ملف صوتي أو فيديو أو Voice) وسأحاول فصل صوت المغني عن "
    "الموسيقى باستخدام الذكاء الاصطناعي.\n\n"
    "بعد المعالجة هتقدر تحمّل الصوت لوحده، أو الموسيقى لوحدها، أو الاثنين."
)

HELP_TEXT = (
    "📚 <b>طريقة الاستخدام</b>\n\n"
    "1. ابعت ملف صوتي أو فيديو أو Voice Message.\n"
    "2. البوت هيحوله لدور في الطابور ويبدأ التحليل.\n"
    "3. هتوصلك رسائل بحالة المعالجة أول بأول.\n"
    "4. لما تخلص، هيوصلك زرار لاختيار الصوت / الموسيقى / الاثنين.\n\n"
    "⚠️ في حدود لحجم الملف ومدة الأغنية، هتظهر لو تجاوزتها."
)


@router.message(Command("start"))
async def cmd_start(message: Message):
    await db.upsert_user(message.from_user.id, message.from_user.username,
                          message.from_user.first_name)
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:help")
async def cb_help(callback: CallbackQuery):
    await callback.message.answer(HELP_TEXT)
    await callback.answer()


@router.callback_query(F.data == "menu:vocal_info")
async def cb_vocal_info(callback: CallbackQuery):
    await callback.answer("ابعت أغنية وهطلعلك الصوت لوحده من الأزرار بعد المعالجة 🎤", show_alert=True)


@router.callback_query(F.data == "menu:music_info")
async def cb_music_info(callback: CallbackQuery):
    await callback.answer("ابعت أغنية وهطلعلك الموسيقى لوحدها من الأزرار بعد المعالجة 🎵", show_alert=True)


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery):
    stats = await db.get_user_stats(callback.from_user.id)
    if not stats:
        await callback.answer("لسه معملتش أي عملية معالجة 🙂", show_alert=True)
        return
    text = (
        f"📊 <b>إحصائياتك</b>\n\n"
        f"عدد الملفات المعالجة: {stats['files_processed']}\n"
        f"إجمالي مدة الصوت المعالج: {int(stats['total_audio_seconds'] // 60)} دقيقة\n"
        f"أول استخدام: {stats['first_seen'][:10]}\n"
    )
    await callback.message.answer(text)
    await callback.answer()


@router.callback_query(F.data == "result:new")
async def cb_new(callback: CallbackQuery):
    await callback.message.answer("ابعت الملف الجديد وهبدأ المعالجة فورًا 🎧")
    await callback.answer()
