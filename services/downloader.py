"""
Сервис скачивания медиа через yt-dlp.
"""

from __future__ import annotations

import asyncio
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable

import yt_dlp

from models import DownloadJob, DownloadResult
from services.cleanup import TempFileService
from settings import Settings

import utils


logger = logging.getLogger(__name__)

ProgressCallback = Callable[[dict], Awaitable[None]]

EXTRACT_INFO_TIMEOUT = 60

USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)


class DownloadCancelled(Exception):
    """Загрузка была отменена пользователем."""


class SlowDownloadCancelled(DownloadCancelled):
    """Загрузка остановлена из-за устойчиво низкой скорости."""


class DownloadAlreadyInProgress(Exception):
    """У пользователя уже есть активная загрузка."""


def _log_progress_error(future):
    exc = future.exception()
    if exc is not None:
        logger.debug("Не удалось передать прогресс загрузки", exc_info=exc)


@dataclass
class ActiveDownloadHandle:
    user_id: int
    job_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)


class DownloadManager:
    def __init__(self, settings: Settings, temp_file_service: TempFileService):
        self._settings = settings
        self._temp_file_service = temp_file_service
        self._semaphore = asyncio.Semaphore(settings.download_semaphore_limit)
        self._active_by_user: dict[int, ActiveDownloadHandle] = {}
        self._lock = asyncio.Lock()

    async def extract_info(self, url: str) -> dict:
        loop = asyncio.get_running_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, lambda: self._extract_info_blocking(url)),
            timeout=EXTRACT_INFO_TIMEOUT,
        )

    def _extract_info_blocking(self, url: str) -> dict:
        with yt_dlp.YoutubeDL(self._build_info_options(url)) as ydl:
            return ydl.extract_info(url, download=False)

    def _build_common_options(self, url: str, youtube_client: str | None = None) -> dict:
        options = {
            "retries": 10,
            "extractor_retries": 10,
            "fragment_retries": 10,
            "socket_timeout": 30,
            "quiet": False,
            "no_warnings": False,
            "http_headers": {
                "User-Agent": random.choice(USER_AGENTS),
                "Referer": url,
            },
        }

        if utils.is_rutube_url(url) and self._settings.rutube_proxy:
            options["proxy"] = self._settings.rutube_proxy

        if utils.is_youtube_url(url):
            options["js_runtimes"] = {"deno": {"path": "/usr/local/bin/deno"}}
            options["remote_components"] = ["ejs:github"]
            if youtube_client:
                options["extractor_args"] = {"youtube": {"player_client": [youtube_client]}}
            if self._settings.youtube_cookies_file:
                cookies_path = self._settings.youtube_cookies_file
                if cookies_path.is_file():
                    options["cookiefile"] = str(cookies_path)
                else:
                    logger.warning(
                        "YOUTUBE_COOKIES_FILE указан, но файл не найден: %s",
                        cookies_path,
                    )

        if utils.is_instagram_url(url) or utils.is_tiktok_url(url):
            options["extract_flat"] = False
            options["skip_download"] = False

        if utils.is_instagram_url(url) and self._settings.instagram_cookies_file:
            cookies_path = self._settings.instagram_cookies_file
            if cookies_path.is_file():
                options["cookiefile"] = str(cookies_path)
            else:
                logger.warning(
                    "INSTAGRAM_COOKIES_FILE указан, но файл не найден: %s",
                    cookies_path,
                )

        return options

    def _build_info_options(self, url: str) -> dict:
        return self._build_common_options(url)

    def _build_download_options(
        self,
        job: DownloadJob,
        output_template: str,
        progress_hook,
        youtube_client: str | None = None,
    ) -> dict:
        options = self._build_common_options(job.url, youtube_client=youtube_client)
        options.update(
            {
                "outtmpl": output_template,
                "progress_hooks": [progress_hook],
                "sleep_interval": 0,
                "concurrent_fragment_downloads": 4,
            }
        )

        if job.choice == "audio":
            options.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                }
            )
        else:
            height = job.quality or "720"
            if job.is_rutube:
                format_spec = (
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/"
                    "best"
                )
            else:
                format_spec = (
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/"
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/"
                    "bestvideo+bestaudio/"
                    "best"
                )

            options.update(
                {
                    "format": format_spec,
                    "merge_output_format": "mp4",
                    "postprocessor_args": {"ffmpeg": ["-movflags", "+faststart"]},
                    "format_sort": ["res", "ext:mp4:m4a", "codec:h264"],
                    "prefer_free_formats": False,
                }
            )

        return options

    async def download(
        self,
        job: DownloadJob,
        progress_callback: ProgressCallback | None = None,
    ) -> DownloadResult:
        handle = ActiveDownloadHandle(user_id=job.user_id, job_id=job.job_id)
        async with self._lock:
            if job.user_id in self._active_by_user:
                raise DownloadAlreadyInProgress(
                    f"У пользователя {job.user_id} уже есть активная загрузка"
                )
            self._active_by_user[job.user_id] = handle

        try:
            async with self._semaphore:
                if handle.cancel_event.is_set():
                    raise DownloadCancelled("cancelled before start")

                loop = asyncio.get_running_loop()
                try:
                    return await asyncio.wait_for(
                        loop.run_in_executor(
                            None,
                            lambda: self._download_blocking(job, handle, progress_callback, loop),
                        ),
                        timeout=self._settings.download_timeout,
                    )
                except asyncio.TimeoutError:
                    handle.cancel_event.set()
                    raise
        finally:
            async with self._lock:
                active = self._active_by_user.get(job.user_id)
                if active and active.job_id == job.job_id:
                    self._active_by_user.pop(job.user_id, None)

    def _download_blocking(
        self,
        job: DownloadJob,
        handle: ActiveDownloadHandle,
        progress_callback: ProgressCallback | None,
        loop: asyncio.AbstractEventLoop,
    ) -> DownloadResult:
        job_dir = self._temp_file_service.create_job_dir(job.job_id)
        output_template = str(job_dir / "%(title)s.%(ext)s")

        slow_started_at: float | None = None
        slow_speed_limit = self._settings.slow_download_speed
        slow_speed_window = self._settings.slow_download_window

        def progress_hook(data: dict):
            nonlocal slow_started_at
            if handle.cancel_event.is_set():
                raise DownloadCancelled("cancelled by user")

            if data.get("status") == "downloading":
                speed = data.get("speed") or 0
                now = time.monotonic()
                if speed < slow_speed_limit:
                    slow_started_at = slow_started_at or now
                    if now - slow_started_at >= slow_speed_window:
                        raise SlowDownloadCancelled(
                            f"download speed below {slow_speed_limit} B/s "
                            f"for {slow_speed_window} seconds"
                        )
                else:
                    slow_started_at = None

            if data.get("status") != "downloading" or progress_callback is None:
                return

            progress = {
                "speed": data.get("speed"),
                "eta": data.get("eta"),
                "downloaded": data.get("downloaded_bytes", 0),
                "total": data.get("total_bytes") or data.get("total_bytes_estimate", 0),
            }
            future = asyncio.run_coroutine_threadsafe(progress_callback(progress), loop)
            future.add_done_callback(_log_progress_error)

        clients = [None, "web_safari"] if utils.is_youtube_url(job.url) else [None]
        for attempt, youtube_client in enumerate(clients):
            try:
                with yt_dlp.YoutubeDL(
                    self._build_download_options(
                        job, output_template, progress_hook, youtube_client=youtube_client
                    )
                ) as ydl:
                    info = ydl.extract_info(job.url, download=True)
                    file_path = self._resolve_downloaded_file(job_dir, ydl, info, job.choice)
                break
            except SlowDownloadCancelled:
                if attempt + 1 >= len(clients):
                    raise
                logger.warning("Медленная загрузка: повтор через YouTube client web_safari")
                for path in job_dir.glob("*"):
                    path.unlink(missing_ok=True)
        else:
            raise RuntimeError("download attempts exhausted")
        if handle.cancel_event.is_set():
            raise DownloadCancelled("cancelled by user")

        if not file_path.exists():
            raise FileNotFoundError(f"Файл не найден после загрузки: {file_path}")

        title = info.get("title", "Без названия")
        uploader = info.get("uploader") or info.get("channel") or "Неизвестный канал"
        quality_label = "MP3" if job.choice == "audio" else f"{job.quality}p"
        return DownloadResult(
            job_id=job.job_id,
            file_path=file_path,
            file_size_bytes=file_path.stat().st_size,
            title=title,
            uploader=uploader,
            media_type=job.choice,
            quality_label=quality_label,
            width=info.get("width"),
            height=info.get("height"),
        )

    def _resolve_downloaded_file(
        self,
        job_dir: Path,
        ydl: yt_dlp.YoutubeDL,
        info: dict,
        choice: str,
    ) -> Path:
        prepared = Path(ydl.prepare_filename(info))
        if choice == "audio":
            candidate = prepared.with_suffix(".mp3")
            if candidate.exists():
                return candidate
            audio_files = sorted(job_dir.glob("*.mp3"))
            if audio_files:
                return audio_files[0]
            return candidate

        if prepared.exists():
            return prepared

        merged_candidate = prepared.with_suffix(".mp4")
        if merged_candidate.exists():
            return merged_candidate

        candidates = sorted(
            (
                path
                for path in job_dir.iterdir()
                if path.is_file() and path.suffix not in {".jpg", ".part", ".tmp"}
            ),
            key=lambda path: path.stat().st_size,
            reverse=True,
        )
        if candidates:
            return candidates[0]
        return merged_candidate

    async def cancel_user_download(self, user_id: int) -> bool:
        async with self._lock:
            handle = self._active_by_user.get(user_id)
            if handle is None:
                return False
            handle.cancel_event.set()
            return True

    async def active_job_ids(self) -> set[str]:
        async with self._lock:
            return {handle.job_id for handle in self._active_by_user.values()}
