"""
Точка входа Telegram-бота.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import shutil
from urllib.parse import urlsplit

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

import config
from dependencies import download_manager, stats_repo, temp_file_service
from handlers import routers


logging.basicConfig(
    format=config.LOG_FORMAT,
    level=getattr(logging, config.LOG_LEVEL.upper(), logging.INFO),
)
logger = logging.getLogger(__name__)


async def validate_startup():
    await temp_file_service.reset_base_dir_async()
    stats_repo.init_db()

    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg не найден в PATH. Установите ffmpeg перед запуском бота.")
    if not shutil.which("ffprobe"):
        raise RuntimeError("ffprobe не найден в PATH. Установите ffmpeg/ffprobe перед запуском бота.")

    if config.USE_LOCAL_BOT_API and config.TELEGRAM_API_BASE:
        parsed = urlsplit(config.TELEGRAM_API_BASE)
        host = parsed.hostname or "localhost"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            reader, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
        except OSError as exc:
            raise RuntimeError(
                f"Не удалось подключиться к локальному Bot API {config.TELEGRAM_API_BASE}."
            ) from exc


def build_session() -> AiohttpSession:
    if config.USE_LOCAL_BOT_API and config.TELEGRAM_API_BASE:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(config.TELEGRAM_API_BASE, is_local=True)
        )
    else:
        session = AiohttpSession()
    session.timeout = config.SESSION_TIMEOUT
    return session


async def periodic_cleanup():
    while True:
        await asyncio.sleep(config.CLEANUP_INTERVAL)
        active_job_ids = await download_manager.active_job_ids()
        removed = temp_file_service.cleanup_stale_dirs(active_job_ids)
        if removed:
            logger.info("🧹 Удалено %s устаревших временных директорий", removed)


async def notify_admin_started(bot: Bot):
    await bot.send_message(
        chat_id=config.ADMIN_ID,
        text="✅ SnatchVideo Bot успешно установлен и запущен.",
    )


async def main():
    await validate_startup()

    bot = Bot(
        token=config.TOKEN,
        session=build_session(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    for router in routers:
        dp.include_router(router)

    cleanup_task = asyncio.create_task(periodic_cleanup())

    logger.info("✅ Бот запущен")
    logger.info("📦 Лимит файла: %s МБ", config.MAX_FILE_SIZE_MB)
    logger.info("📊 Статистика: %s", config.STATS_DB_PATH)
    if config.RUTUBE_PROXY:
        logger.info("🌐 Rutube прокси: %s", config.MASKED_RUTUBE_PROXY)
    if config.YOUTUBE_COOKIES_FILE:
        cookies_status = "ok" if config.YOUTUBE_COOKIES_FILE.is_file() else "MISSING"
        logger.info("🍪 YouTube cookies: %s (%s)", config.YOUTUBE_COOKIES_FILE, cookies_status)
    if config.INSTAGRAM_COOKIES_FILE:
        ig_status = "ok" if config.INSTAGRAM_COOKIES_FILE.is_file() else "MISSING"
        logger.info("🍪 Instagram cookies: %s (%s)", config.INSTAGRAM_COOKIES_FILE, ig_status)
    logger.info(
        "🤖 Telegram API: %s",
        config.TELEGRAM_API_BASE if config.USE_LOCAL_BOT_API else "official",
    )

    try:
        await bot.get_me()
        await notify_admin_started(bot)
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
