"""
keyboards/main.py
Inline keyboards for the regular user flow.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎤 استخراج الصوت", callback_data="menu:vocal_info"),
            InlineKeyboardButton(text="🎵 استخراج الموسيقى", callback_data="menu:music_info"),
        ],
        [
            InlineKeyboardButton(text="📚 المساعدة", callback_data="menu:help"),
            InlineKeyboardButton(text="📊 إحصائياتي", callback_data="menu:stats"),
        ],
    ])


def result_kb(job_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎤 الصوت فقط", callback_data=f"result:vocal:{job_id}"),
            InlineKeyboardButton(text="🎵 الموسيقى فقط", callback_data=f"result:music:{job_id}"),
        ],
        [
            InlineKeyboardButton(text="📥 تحميل الاثنين", callback_data=f"result:both:{job_id}"),
        ],
        [
            InlineKeyboardButton(text="🔄 معالجة ملف آخر", callback_data="result:new"),
        ],
    ])
