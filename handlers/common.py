"""
Общие команды бота.
"""

from __future__ import annotations

import asyncio
import sys

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from dependencies import download_manager
from handlers.session_utils import cleanup_bot_messages, save_bot_message
from handlers.states import DownloadStates


router = Router()
# /restart фильтруется по admin_id, но остальные команды в этом роутере имеют смысл
# только в приватных чатах. Фильтр на роутер-уровне убирает повторяющиеся
# проверки в каждом хендлере.
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot):
    await cleanup_bot_messages(bot, state, message.chat.id)
    await state.clear()
    await state.set_state(DownloadStates.waiting_link)
    msg = await message.answer(
        "👋 Привет! Я бот для скачивания видео.\n\n"
        "📎 Отправь ссылку на видео с:\n"
        "  • YouTube\n"
        "  • Rutube\n"
        "  • VK\n"
        "  • Instagram\n"
        "  • TikTok\n\n"
        "📊 /mystats — твоя статистика загрузок"
    )
    await save_bot_message(state, msg)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    cancel_requested = await download_manager.cancel_user_download(user_id)

    await cleanup_bot_messages(bot, state, message.chat.id)
    await state.clear()
    await state.set_state(DownloadStates.waiting_link)

    text = "⏸️ Отмена запрошена. Останавливаю текущую загрузку..." if cancel_requested else "🚫 Операция отменена."
    msg = await message.answer(text)
    await save_bot_message(state, msg)


@router.message(Command("restart"))
async def cmd_restart(message: Message, bot: Bot):
    if message.from_user.id != config.ADMIN_ID:
        return

    await message.answer("🔄 Бот уходит на перезагрузку. Вернусь через пару секунд!")
    await bot.session.close()
    await asyncio.sleep(0.2)
    # Чистый exit: systemd с Restart=always (или Restart=on-success) сам поднимет
    # процесс заново. Это правильнее, чем os.execv: cgroup пересоздаётся,
    # счётчики StartLimitBurst/RestartSec сбрасываются, никаких unsanitised
    # state'ов внутри уже-стартовавшего интерпретатора.
    sys.exit(0)
