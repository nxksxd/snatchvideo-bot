"""
Общие singleton-зависимости приложения.

Все singleton'ы инициализируются лениво через ``functools.lru_cache``-фабрики,
чтобы импорт модуля сам по себе не дёргал ``Settings.from_env()``. Это нужно,
чтобы тесты могли импортировать любой код, не задавая ``TELEGRAM_BOT_TOKEN``.

Для обратной совместимости старые имена (``stats_repo``, ``download_manager``,
``temp_file_service``, ``media_sender``) выставляются как module-level атрибуты
через ``__getattr__``: первый доступ строит соответствующий объект.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from repositories import StatsRepository
    from services.cleanup import TempFileService
    from services.downloader import DownloadManager
    from services.sender import MediaSender


@lru_cache(maxsize=1)
def get_stats_repo() -> "StatsRepository":
    from repositories import StatsRepository
    from settings import settings

    return StatsRepository(settings.stats_db_path, cache_ttl=settings.stats_cache_ttl)


@lru_cache(maxsize=1)
def get_temp_file_service() -> "TempFileService":
    from services.cleanup import TempFileService
    from settings import settings

    return TempFileService(settings.temp_dir, stale_after_seconds=settings.temp_file_ttl)


@lru_cache(maxsize=1)
def get_download_manager() -> "DownloadManager":
    from services.downloader import DownloadManager
    from settings import settings

    return DownloadManager(settings, get_temp_file_service())


@lru_cache(maxsize=1)
def get_media_sender() -> "MediaSender":
    from services.sender import MediaSender

    return MediaSender()


_FACTORIES = {
    "stats_repo": get_stats_repo,
    "temp_file_service": get_temp_file_service,
    "download_manager": get_download_manager,
    "media_sender": get_media_sender,
}


def __getattr__(name: str):
    factory = _FACTORIES.get(name)
    if factory is None:
        raise AttributeError(f"module 'dependencies' has no attribute {name!r}")
    return factory()


def reset_for_tests() -> None:
    """Сбросить все ленивые кэши. Полезно в тестах между прогонами."""
    for factory in _FACTORIES.values():
        factory.cache_clear()
