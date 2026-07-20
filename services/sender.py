"""
Отправка скачанных файлов пользователю.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path

from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramEntityTooLarge,
    TelegramNetworkError,
    TelegramRetryAfter,
    TelegramServerError,
)
from aiogram.types import FSInputFile, Message

from models import DownloadResult
from services.video_compat import is_ios_compatible_video

import utils


logger = logging.getLogger(__name__)


class MediaSender:
    async def send_result(self, message: Message, result: DownloadResult, source_url: str):
        caption = self._build_caption(result, source_url)
        if result.media_type == "audio":
            await self._send_with_retry(
                lambda: message.answer_audio(
                    audio=FSInputFile(result.file_path),
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    performer=result.uploader,
                    title=result.title,
                )
            )
            return

        video_path = await self._prepare_video_for_delivery(result.file_path, source_url)
        thumbnail_path = await self._create_thumbnail(video_path)
        send_kwargs = {
            "video": FSInputFile(video_path),
            "caption": caption,
            "parse_mode": ParseMode.HTML,
            "width": result.width,
            "height": result.height,
        }
        if thumbnail_path and thumbnail_path.exists():
            send_kwargs["thumbnail"] = FSInputFile(thumbnail_path)

        await self._send_with_retry(lambda: message.answer_video(**send_kwargs))

    async def _send_with_retry(self, coro_factory, retries: int = 2, delay: int = 5):
        """
        Отправка с ретраями для типичных временных ошибок Telegram-API.

        Перехватывает:
          * ``TelegramRetryAfter`` (HTTP 429): спим ровно столько, сколько просит API.
          * ``TelegramServerError`` (5xx): экспоненциальный backoff.
          * ``TelegramNetworkError`` (сеть/таймаут на нашей стороне): обычный delay.
          * Любое другое исключение с подстрокой ``timeout`` (на случай старых версий
            aiogram или прокси-обёрток): обычный delay.

        Для всех прочих исключений сразу пробрасываем — у вызывающего своя логика.
        """
        for attempt in range(retries + 1):
            try:
                return await coro_factory()
            except TelegramRetryAfter as exc:
                if attempt >= retries:
                    raise
                wait = max(int(getattr(exc, "retry_after", 0) or 0), 1)
                logger.warning(
                    "Telegram попросил подождать %s сек (RetryAfter), попытка %s/%s",
                    wait, attempt + 1, retries + 1,
                )
                await asyncio.sleep(wait)
            except TelegramServerError:
                if attempt >= retries:
                    raise
                wait = delay * (2 ** attempt)
                logger.warning(
                    "Telegram-сервер вернул 5xx, повтор через %s сек (попытка %s/%s)",
                    wait, attempt + 1, retries + 1,
                )
                await asyncio.sleep(wait)
            except TelegramEntityTooLarge:
                raise
            except TelegramNetworkError as exc:
                if attempt >= retries:
                    raise
                logger.warning(
                    "Сетевая ошибка Telegram: %s; повтор через %s сек (попытка %s/%s)",
                    exc, delay, attempt + 1, retries + 1,
                )
                await asyncio.sleep(delay)
            except Exception as exc:
                if "timeout" in str(exc).lower() and attempt < retries:
                    logger.warning("Таймаут отправки, повтор через %s сек", delay)
                    await asyncio.sleep(delay)
                    continue
                raise

    async def _prepare_video_for_delivery(self, video_path: Path, source_url: str) -> Path:
        if not await self._should_transcode_for_ios(video_path, source_url):
            return video_path

        transcoded_path = await self._transcode_to_ios_compatible(video_path)
        return transcoded_path or video_path

    async def _should_transcode_for_ios(self, video_path: Path, source_url: str) -> bool:
        source_label = utils.get_domain_label(source_url)
        probe = await self._probe_media(video_path)
        if probe is None:
            # Если ffprobe недоступен или файл не разобрался, форсируем только Instagram.
            return utils.is_instagram_url(source_url)

        streams = probe.get("streams", [])
        video_stream = next((item for item in streams if item.get("codec_type") == "video"), {})
        audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), {})

        video_codec = video_stream.get("codec_name")
        audio_codec = audio_stream.get("codec_name")
        pix_fmt = video_stream.get("pix_fmt")

        compatible = is_ios_compatible_video(video_codec, audio_codec, pix_fmt)
        if compatible:
            return False

        # Instagram оставляем в строгом режиме, там реально чаще всплывают
        # нестандартные ролики, от которых страдает Telegram iOS.
        if utils.is_instagram_url(source_url):
            logger.info(
                "Принудительная перекодировка для %s: codec=%s audio=%s pix_fmt=%s file=%s",
                source_label,
                video_codec,
                audio_codec,
                pix_fmt,
                video_path.name,
            )
            return True

        # Для остальных площадок сберегаем CPU слабого VPS и не трогаем файлы,
        # если уже есть H.264 видео и AAC-аудио. Проблемный pix_fmt сам по себе
        # не всегда оправдывает дорогую полную перекодировку.
        if video_codec == "h264" and audio_codec in (None, "aac"):
            logger.info(
                "Пропускаю перекодировку для %s: codec=%s audio=%s pix_fmt=%s file=%s",
                source_label,
                video_codec,
                audio_codec,
                pix_fmt,
                video_path.name,
            )
            return False

        logger.info(
            "Перекодировка для iOS: codec=%s audio=%s pix_fmt=%s source=%s file=%s",
            video_codec,
            audio_codec,
            pix_fmt,
            source_label,
            video_path.name,
        )
        return True

    async def _probe_media(self, video_path: Path) -> dict | None:
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-of",
                "json",
                str(video_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
        except FileNotFoundError:
            logger.warning("ffprobe не найден, пропускаю анализ совместимости")
            return None

        if proc.returncode != 0:
            logger.warning(
                "ffprobe не смог проанализировать файл %s: %s",
                video_path,
                stderr.decode(errors="ignore").strip(),
            )
            return None

        try:
            return json.loads(stdout.decode() or "{}")
        except json.JSONDecodeError:
            logger.warning("ffprobe вернул невалидный JSON для %s", video_path)
            return None

    async def _transcode_to_ios_compatible(self, video_path: Path) -> Path | None:
        output_path = video_path.with_name(f"{video_path.stem}.ios.mp4")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0?",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "24",
                "-pix_fmt",
                "yuv420p",
                "-profile:v",
                "high",
                "-level:v",
                "4.1",
                "-threads",
                str(min(2, (os.cpu_count() or 2))),
                "-movflags",
                "+faststart",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()
        except FileNotFoundError:
            logger.warning("ffmpeg не найден, пропускаю перекодировку")
            return None

        if proc.returncode != 0 or not output_path.exists():
            logger.warning(
                "Не удалось перекодировать видео для iOS: %s",
                stderr.decode(errors="ignore").strip(),
            )
            return None

        logger.info("Создан iOS-совместимый файл: %s", output_path.name)
        return output_path

    async def _create_thumbnail(self, video_path: Path) -> Path | None:
        thumbnail_path = video_path.with_suffix(video_path.suffix + ".jpg")
        try:
            proc = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                "00:00:01",
                "-vframes",
                "1",
                "-vf",
                "scale='if(gt(iw,ih),320,-2)':'if(gt(iw,ih),-2,320)'",
                "-q:v",
                "5",
                "-y",
                str(thumbnail_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0 or not thumbnail_path.exists():
                return None
            return thumbnail_path
        except Exception:
            logger.warning("Не удалось создать превью", exc_info=True)
            return None

    def _build_caption(self, result: DownloadResult, source_url: str) -> str:
        hashtag = "#" + "".join(char for char in result.uploader if char.isalnum() or char == "_")
        title_escaped = utils.escape_html(result.title)
        url_escaped = utils.escape_html(source_url)
        return (
            f'📹 <a href="{url_escaped}">{title_escaped}</a>\n'
            f"👤 {hashtag}\n"
            f"📼 Качество: {result.quality_label} | @SnatchClip_bot"
        )
