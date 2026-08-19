"""
main.py
Entry point. Runs long-polling for RUN_DURATION_MINUTES then exits cleanly,
so it works with a scheduled GitHub Actions workflow that restarts the bot
every 6 hours (avoiding 409 Conflict from overlapping getUpdates calls).
"""
import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db
from handlers import start, audio, admin
from services.cleanup import cleanup_loop
from utils.logger import logger


async def main():
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(audio.router)

    # Make sure no other instance is polling (helps with 409 Conflict
    # right after a redeploy).
    await bot.delete_webhook(drop_pending_updates=False)

    cleanup_task = asyncio.create_task(cleanup_loop())

    run_seconds = config.RUN_DURATION_MINUTES * 60
    logger.info(f"Bot starting. Will run for {config.RUN_DURATION_MINUTES} minutes then exit cleanly.")

    polling_task = asyncio.create_task(dp.start_polling(bot))

    try:
        await asyncio.wait_for(polling_task, timeout=run_seconds)
    except asyncio.TimeoutError:
        logger.info("Run duration reached. Shutting down gracefully for the next scheduled run.")
    finally:
        cleanup_task.cancel()
        await dp.stop_polling()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
