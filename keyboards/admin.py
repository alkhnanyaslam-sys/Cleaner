"""
keyboards/admin.py
Inline keyboards for the admin panel.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 الإحصائيات", callback_data="admin:stats"),
            InlineKeyboardButton(text="🖥️ حالة السيرفر", callback_data="admin:system"),
        ],
        [
            InlineKeyboardButton(text="📢 رسالة جماعية", callback_data="admin:broadcast"),
        ],
        [
            InlineKeyboardButton(text="🚫 حظر مستخدم", callback_data="admin:ban"),
            InlineKeyboardButton(text="🔓 فك حظر", callback_data="admin:unban"),
        ],
        [
            InlineKeyboardButton(text="🔧 الإعدادات", callback_data="admin:settings"),
            InlineKeyboardButton(text="📝 السجلات", callback_data="admin:logs"),
        ],
        [
            InlineKeyboardButton(text="🗑️ تنظيف الملفات المؤقتة", callback_data="admin:cleanup"),
        ],
    ])


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ رجوع", callback_data="admin:menu")]
    ])
