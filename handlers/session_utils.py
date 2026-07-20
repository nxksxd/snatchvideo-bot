"""
Утилиты для краткоживущих сообщений и прогресса.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message


logger = logging.getLogger(__name__)


async def save_bot_message(state: FSMContext, message: Message):
    data = await state.get_data()
    bot_messages: list[int] = data.get("bot_messages", [])
    if message.message_id not in bot_messages:
        bot_messages.append(message.message_id)
        await state.update_data(bot_messages=bot_messages)


async def cleanup_bot_messages(bot: Bot, state: FSMContext, chat_id: int):
    data = await state.get_data()
    for msg_id in data.get("bot_messages", []):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            continue
    await state.update_data(bot_messages=[])


async def update_progress_message(bot: Bot, state: FSMContext, chat_id: int, message_id: int):
    last_text = ""
    while True:
        data = await state.get_data()
        if data.get("download_done", False):
            break

        progress = data.get("progress", {})
        speed = progress.get("speed")
        eta = progress.get("eta")
        downloaded = progress.get("downloaded", 0)
        total = progress.get("total", 0)

        if total and downloaded:
            percent = downloaded / total * 100
            status = f"⏳ {percent:.1f}%"
        else:
            status = "⏳ Скачиваю..."

        if eta:
            minutes, seconds = divmod(int(eta), 60)
            time_str = f"{minutes} мин {seconds} сек" if minutes else f"{seconds} сек"
            status += f" осталось ~{time_str}"

        if speed:
            status += f" ({speed / 1024 / 1024:.1f} МБ/с)"

        if status != last_text:
            try:
                await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=status)
                last_text = status
            except Exception:
                break

        await asyncio.sleep(1)


async def stop_progress(state: FSMContext):
    await state.update_data(download_done=True)
