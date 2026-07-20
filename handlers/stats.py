"""
Команды статистики.
"""

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

import config
from dependencies import stats_repo
from handlers.session_utils import save_bot_message
import utils


router = Router()
router.message.filter(F.chat.type == "private")


@router.message(Command("stats"))
async def cmd_stats(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != config.ADMIN_ID:
        msg = await message.answer("❌ Эта команда доступна только администратору.")
        await save_bot_message(state, msg)
        return

    stats = stats_repo.get_global_stats()
    text = utils.format_global_stats(stats)
    msg = await message.answer(text, parse_mode=ParseMode.HTML)
    await save_bot_message(state, msg)


@router.message(Command("mystats"))
async def cmd_mystats(message: Message, state: FSMContext, bot: Bot):
    stats = stats_repo.get_user_stats(message.from_user.id)
    text = utils.format_user_stats(stats)
    msg = await message.answer(text, parse_mode=ParseMode.HTML)
    await save_bot_message(state, msg)
