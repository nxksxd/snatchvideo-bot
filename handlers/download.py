"""
Обработчики сценария скачивания.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from uuid import uuid4

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

import config
from dependencies import download_manager, media_sender, stats_repo, temp_file_service
from handlers.session_utils import (
    cleanup_bot_messages,
    save_bot_message,
    stop_progress,
    update_progress_message,
)
from handlers.states import DownloadStates
from models import DownloadJob
from services.downloader import DownloadAlreadyInProgress, DownloadCancelled
from services.media_info import build_media_info_result
import utils


logger = logging.getLogger(__name__)
router = Router()
# Все хендлеры в этом роутере имеют смысл только в приватных чатах.
router.message.filter(F.chat.type == "private")
router.callback_query.filter(F.message.chat.type == "private")


@router.message(
    StateFilter(None, DownloadStates.waiting_link, DownloadStates.waiting_quality),
    F.text,
)
async def handle_link(message: Message, state: FSMContext, bot: Bot):
    raw_url = message.text.strip()
    current_state = await state.get_state()
    url = utils.normalize_url(raw_url)

    if not utils.is_url(url):
        if current_state == DownloadStates.waiting_quality.state:
            msg = await message.answer(
                "⏳ Сейчас ожидается выбор качества. "
                "Нажмите кнопку выше, отправьте новую ссылку или используйте /cancel."
            )
            await save_bot_message(state, msg)
        elif current_state == DownloadStates.waiting_link.state:
            msg = await message.answer("❌ Пожалуйста, отправьте корректную ссылку.")
            await save_bot_message(state, msg)
        return

    if not utils.is_supported_url(url):
        msg = await message.answer(
            "❌ Поддерживаются только YouTube, Rutube, VK, Instagram и TikTok видео."
        )
        await save_bot_message(state, msg)
        await state.set_state(DownloadStates.waiting_link)
        return

    await cleanup_bot_messages(bot, state, message.chat.id)
    await state.clear()
    await state.set_state(DownloadStates.waiting_link)
    await state.update_data(
        url=url,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    msg = await message.answer("🔍 Получаю информацию о видео...")
    await save_bot_message(state, msg)

    info = None
    try:
        info = await download_manager.extract_info(url)
    except Exception:
        logger.warning("Не удалось получить метаданные видео для %s", url, exc_info=True)

    media_info = build_media_info_result(url, info, config.DEFAULT_QUALITIES)
    keyboard = utils.build_quality_keyboard(
        media_info.qualities,
        media_info.quality_sizes,
        media_info.fallback_mode,
    )

    if media_info.title:
        prompt_text = (
            f"🎬 <b>{utils.escape_html(media_info.title)}</b>\n\n"
            "Выберите качество:"
        )
    else:
        prompt_text = "🎬 Выберите качество:"

    await cleanup_bot_messages(bot, state, message.chat.id)
    prompt = await message.answer(prompt_text, reply_markup=keyboard)
    await save_bot_message(state, prompt)
    await state.update_data(
        url=url,
        quality_sizes=media_info.quality_sizes,
        fallback_mode=media_info.fallback_mode,
        is_rutube=media_info.is_rutube,
    )
    await state.set_state(DownloadStates.waiting_quality)


@router.callback_query(
    StateFilter(DownloadStates.waiting_quality),
    F.data.regexp(r"^(video_\d+|audio)$"),
)
async def quality_choice(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()

    data = await state.get_data()
    url = data.get("url")
    user_id = data.get("user_id")
    chat_id = callback.message.chat.id
    choice = callback.data
    fallback_mode = data.get("fallback_mode", False)
    is_rutube = data.get("is_rutube", False)
    quality_sizes = data.get("quality_sizes", {})

    if not url or not user_id:
        await callback.message.edit_text("❌ Ошибка: ссылка больше не доступна. Отправьте её заново.")
        await state.clear()
        await state.set_state(DownloadStates.waiting_link)
        return

    if choice != "audio" and not fallback_mode:
        height = choice.split("_", 1)[1]
        estimated_bytes = quality_sizes.get(height, 0)
        if estimated_bytes > config.MAX_FILE_SIZE:
            sorted_qualities = sorted(quality_sizes.keys(), key=int, reverse=True)
            await callback.message.edit_text(
                f"❌ Файл слишком большой: примерно {estimated_bytes / 1024 / 1024:.0f} МБ.\n"
                f"Максимальный размер: {config.MAX_FILE_SIZE_MB} МБ.\n\n"
                "Пожалуйста, выберите качество ниже 👇"
            )
            keyboard = utils.build_quality_keyboard(sorted_qualities, quality_sizes, fallback_mode=False)
            msg = await callback.message.answer("🎬 Выберите качество:", reply_markup=keyboard)
            await save_bot_message(state, msg)
            return

    await callback.message.edit_text("⏳ Скачиваю и обрабатываю...")
    progress_message_id = callback.message.message_id
    bot_messages = data.get("bot_messages", [])
    if progress_message_id not in bot_messages:
        bot_messages.append(progress_message_id)
    await state.update_data(bot_messages=bot_messages, progress={}, download_done=False)

    progress_task = asyncio.create_task(
        update_progress_message(bot, state, chat_id, progress_message_id)
    )

    job_id = f"{user_id}_{uuid4().hex[:10]}"
    job = DownloadJob(
        job_id=job_id,
        user_id=user_id,
        url=url,
        choice="audio" if choice == "audio" else "video",
        quality=None if choice == "audio" else choice.split("_", 1)[1],
        is_rutube=is_rutube,
    )

    async def on_progress(progress: dict):
        await state.update_data(progress=progress)

    try:
        result = await download_manager.download(job, progress_callback=on_progress)
        await stop_progress(state)
        await cleanup_bot_messages(bot, state, chat_id)

        if result.file_size_bytes > config.MAX_FILE_SIZE:
            actual_mb = result.file_size_bytes / 1024 / 1024
            logger.info(
                "Скачанный файл превышает лимит: %.0f МБ > %d МБ (job_id=%s)",
                actual_mb,
                config.MAX_FILE_SIZE_MB,
                job.job_id,
            )
            await callback.message.answer(
                f"❌ Файл получился слишком большим: {actual_mb:.0f} МБ.\n"
                f"Максимальный размер: {config.MAX_FILE_SIZE_MB} МБ.\n\n"
                "Попробуйте выбрать качество ниже или скачать только аудио."
            )
            return

        sending_msg = await callback.message.answer(
            "📤 Файл скачан! Отправляю пользователю, это может занять немного времени..."
        )
        await save_bot_message(state, sending_msg)

        await media_sender.send_result(callback.message, result, url)

        try:
            await bot.delete_message(chat_id, sending_msg.message_id)
        except Exception:
            logger.debug("Не удалось удалить служебное сообщение отправки", exc_info=True)

        stats_repo.record_download(
            user_id=user_id,
            username=data.get("username"),
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            domain=utils.get_domain_label(url),
            media_type=result.media_type,
            quality="MP3" if result.media_type == "audio" else job.quality,
            file_size=result.file_size_bytes,
            url=url,
            title=result.title,
        )
    except DownloadAlreadyInProgress:
        logger.info("Пользователь %s попытался запустить параллельную загрузку", user_id)
        await stop_progress(state)
        await cleanup_bot_messages(bot, state, chat_id)
        await callback.message.answer(
            "⏳ У вас уже идёт загрузка. Дождитесь её завершения или отмените через /cancel."
        )
    except DownloadCancelled:
        logger.info("Загрузка %s отменена пользователем %s", job.job_id, user_id)
        await stop_progress(state)
        await cleanup_bot_messages(bot, state, chat_id)
        await callback.message.answer("❌ Загрузка отменена пользователем.")
    except asyncio.TimeoutError:
        logger.warning("Загрузка %s превысила таймаут", job.job_id)
        await stop_progress(state)
        await cleanup_bot_messages(bot, state, chat_id)
        await callback.message.answer(
            "❌ Превышено время ожидания загрузки.\n"
            "Попробуйте выбрать качество ниже или повторить попытку позже."
        )
    except Exception:
        logger.exception("Ошибка загрузки для job_id=%s", job.job_id)
        await stop_progress(state)
        await cleanup_bot_messages(bot, state, chat_id)
        hint = "Попробуйте отправить ссылку заново или выбрать другое качество."
        if is_rutube and config.RUTUBE_PROXY:
            hint += "\nЕсли проблема повторяется, проверьте доступность прокси."
        await callback.message.answer(f"❌ Не удалось скачать файл.\n{hint}")
    finally:
        progress_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await progress_task
        temp_file_service.cleanup_job_dir(job_id)
        await state.clear()
        await state.set_state(DownloadStates.waiting_link)
