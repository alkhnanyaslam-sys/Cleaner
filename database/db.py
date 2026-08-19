"""
database/db.py
SQLite database layer (async, via aiosqlite).
Designed so the queries here are simple enough to port to PostgreSQL later
(no SQLite-only syntax beyond AUTOINCREMENT).
"""
import datetime
import os
from typing import Optional

import aiosqlite

from config import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    first_seen TEXT NOT NULL,
    last_seen TEXT NOT NULL,
    files_processed INTEGER NOT NULL DEFAULT 0,
    total_audio_seconds REAL NOT NULL DEFAULT 0,
    is_banned INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    finished_at TEXT,
    duration_seconds REAL,
    processing_time_seconds REAL,
    error TEXT,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


async def init_db() -> None:
    os.makedirs(os.path.dirname(config.DATABASE_URL) or ".", exist_ok=True)
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.executescript(SCHEMA)
        await db.commit()


def _now() -> str:
    return datetime.datetime.utcnow().isoformat()


async def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        now = _now()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, first_name, first_seen, last_seen) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username, first_name, now, now),
            )
        else:
            await db.execute(
                "UPDATE users SET username = ?, first_name = ?, last_seen = ? WHERE user_id = ?",
                (username, first_name, now, user_id),
            )
        await db.commit()


async def is_banned(user_id: int) -> bool:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        cur = await db.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return bool(row and row[0])


async def set_banned(user_id: int, banned: bool) -> None:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
        await db.commit()


async def create_job(job_id: str, user_id: int) -> None:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO jobs (job_id, user_id, status, created_at) VALUES (?, ?, ?, ?)",
            (job_id, user_id, "queued", _now()),
        )
        await db.commit()


async def update_job(job_id: str, **fields) -> None:
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [job_id]
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.execute(f"UPDATE jobs SET {cols} WHERE job_id = ?", values)
        await db.commit()


async def finish_job(job_id: str, success: bool, duration_seconds: float = 0,
                      processing_time_seconds: float = 0, error: str = None) -> None:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.execute(
            "UPDATE jobs SET status = ?, finished_at = ?, duration_seconds = ?, "
            "processing_time_seconds = ?, error = ? WHERE job_id = ?",
            ("done" if success else "failed", _now(), duration_seconds,
             processing_time_seconds, error, job_id),
        )
        if success:
            await db.execute(
                "UPDATE users SET files_processed = files_processed + 1, "
                "total_audio_seconds = total_audio_seconds + ? WHERE user_id = "
                "(SELECT user_id FROM jobs WHERE job_id = ?)",
                (duration_seconds, job_id),
            )
        await db.commit()


async def count_jobs_today(user_id: int) -> int:
    today = datetime.date.today().isoformat()
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM jobs WHERE user_id = ? AND created_at >= ? AND status != 'failed'",
            (user_id, today),
        )
        row = await cur.fetchone()
        return row[0] if row else 0


async def get_user_stats(user_id: int) -> Optional[dict]:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        return dict(row) if row else None


async def get_global_stats() -> dict:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        cur = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM users WHERE last_seen >= ?",
            ((datetime.datetime.utcnow() - datetime.timedelta(days=1)).isoformat(),),
        )
        active_users = (await cur.fetchone())[0]

        cur = await db.execute("SELECT COUNT(*) FROM jobs WHERE status = 'done'")
        processed = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT AVG(processing_time_seconds) FROM jobs WHERE status = 'done'"
        )
        avg_time = (await cur.fetchone())[0] or 0

        cur = await db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='done' AND created_at >= ?",
            (datetime.date.today().isoformat(),),
        )
        today_count = (await cur.fetchone())[0]

        cur = await db.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='done' AND created_at >= ?",
            ((datetime.date.today() - datetime.timedelta(days=30)).isoformat(),),
        )
        month_count = (await cur.fetchone())[0]

        return {
            "total_users": total_users,
            "active_users": active_users,
            "files_processed": processed,
            "avg_processing_time": avg_time,
            "today_count": today_count,
            "month_count": month_count,
        }


async def get_setting(key: str, default: str = None) -> Optional[str]:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default


async def set_setting(key: str, value: str) -> None:
    async with aiosqlite.connect(config.DATABASE_URL) as db:
        await db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()
