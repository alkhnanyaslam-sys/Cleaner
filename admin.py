"""
handlers/admin.py
Full in-Telegram admin panel.
"""
import glob
import os

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from config import config
from database import db
from keyboards.admin import admin_menu_kb, admin_back_kb
from services.cleanup import delete_path
from utils.logger import logger
from utils.system_info import get_system_status

router = Router(name="admin")


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_ban_id = State()
    waiting_unban_id = State()


def _is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not _is_admin(message.from_user.id):
        return
    await message.answer("🛠️ <b>لوحة تحكم الأدمن</b>", reply_markup=admin_menu_kb())


@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🛠️ <b>لوحة تحكم الأدمن</b>", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    stats = await db.get_global_stats()
    text = (
        "📊 <b>إحصائيات البوت</b>\n\n"
        f"👥 عدد المستخدمين: {stats['total_users']}\n"
        f"🟢 نشطون آخر 24 ساعة: {stats['active_users']}\n"
        f"📦 عدد الملفات المعالجة: {stats['files_processed']}\n"
        f"⏱️ متوسط وقت المعالجة: {stats['avg_processing_time']:.1f} ثانية\n"
        f"📈 اليوم: {stats['today_count']} | آخر 30 يوم: {stats['month_count']}\n"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:system")
async def cb_admin_system(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    s = get_system_status()
    text = (
        "🖥️ <b>حالة السيرفر</b>\n\n"
        f"CPU: {s['cpu_percent']:.1f}%\n"
        f"RAM: {s['ram_percent']:.1f}% ({s['ram_used_mb']:.0f}MB / {s['ram_total_mb']:.0f}MB)\n"
        f"القرص: {s['disk_used_gb']:.1f}GB / {s['disk_total_gb']:.1f}GB\n"
        f"الجهاز المستخدم: {s['device']}\n"
        f"GPU: {s['gpu']}\n"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("📢 ابعت الرسالة اللي عايز ترسلها لكل المستخدمين:",
                                      reply_markup=admin_back_kb())
    await state.set_state(AdminStates.waiting_broadcast)
    await callback.answer()


@router.message(AdminStates.waiting_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()

    async with __import__("aiosqlite").connect(config.DATABASE_URL) as conn:
        cur = await conn.execute("SELECT user_id FROM users WHERE is_banned = 0")
        rows = await cur.fetchall()

    sent, failed = 0, 0
    for (uid,) in rows:
        try:
            await bot.send_message(uid, message.text)
            sent += 1
        except Exception:
            failed += 1
    await message.answer(f"✅ تم الإرسال. نجح: {sent} | فشل: {failed}")


@router.callback_query(F.data == "admin:ban")
async def cb_admin_ban(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🚫 ابعت الـ User ID اللي عايز تحظره:", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.waiting_ban_id)
    await callback.answer()


@router.message(AdminStates.waiting_ban_id)
async def process_ban(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("⚠️ لازم رقم صحيح.")
        return
    uid = int(message.text.strip())
    await db.set_banned(uid, True)
    await message.answer(f"✅ تم حظر المستخدم {uid}.")


@router.callback_query(F.data == "admin:unban")
async def cb_admin_unban(callback: CallbackQuery, state: FSMContext):
    if not _is_admin(callback.from_user.id):
        return
    await callback.message.edit_text("🔓 ابعت الـ User ID اللي عايز تفك حظره:", reply_markup=admin_back_kb())
    await state.set_state(AdminStates.waiting_unban_id)
    await callback.answer()


@router.message(AdminStates.waiting_unban_id)
async def process_unban(message: Message, state: FSMContext):
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    if not message.text.strip().isdigit():
        await message.answer("⚠️ لازم رقم صحيح.")
        return
    uid = int(message.text.strip())
    await db.set_banned(uid, False)
    await message.answer(f"✅ تم فك حظر المستخدم {uid}.")


@router.callback_query(F.data == "admin:settings")
async def cb_admin_settings(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    text = (
        "🔧 <b>الإعدادات الحالية</b>\n\n"
        f"الحد الأقصى لحجم الملف: {config.MAX_FILE_SIZE_MB}MB\n"
        f"الحد الأقصى لمدة الأغنية: {config.MAX_DURATION_SECONDS // 60} دقيقة\n"
        f"عدد الملفات المتزامنة لكل مستخدم: {config.MAX_CONCURRENT_PER_USER}\n"
        f"عدد العمليات لكل مستخدم يوميًا: {config.MAX_JOBS_PER_USER_DAILY}\n"
        f"النموذج المستخدم: {config.MODEL_NAME}\n\n"
        "لتغيير أي قيمة، عدّل ملف .env / GitHub Secrets وأعد التشغيل."
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:logs")
async def cb_admin_logs(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    try:
        with open("logs/bot.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-25:]
        text = "📝 <b>آخر السجلات</b>\n\n<code>" + "".join(lines)[-3500:] + "</code>"
    except FileNotFoundError:
        text = "📝 لا توجد سجلات بعد."
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:cleanup")
async def cb_admin_cleanup(callback: CallbackQuery):
    if not _is_admin(callback.from_user.id):
        return
    count = 0
    for path in glob.glob(os.path.join(config.TEMP_DIR, "*")):
        delete_path(path)
        count += 1
    await callback.message.edit_text(f"🗑️ تم حذف {count} من الملفات المؤقتة.",
                                      reply_markup=admin_back_kb())
    await callback.answer()
