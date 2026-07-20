"""
Совместимый слой поверх settings.py.

Все атрибуты резолвятся лениво через PEP 562 ``__getattr__`` —
``import config`` сам по себе не дёргает ``Settings.from_env()`` и не требует
наличия переменных окружения. Загрузка происходит при первом обращении к
конкретному атрибуту (например ``config.TOKEN``).
"""

from __future__ import annotations

from typing import Any


_FACTORIES: dict[str, Any] = {
    "TOKEN": lambda s: s.token,
    "ADMIN_ID": lambda s: s.admin_id,
    "RUTUBE_PROXY": lambda s: s.rutube_proxy,
    "MASKED_RUTUBE_PROXY": lambda s: s.masked_proxy,
    "YOUTUBE_COOKIES_FILE": lambda s: s.youtube_cookies_file,
    "INSTAGRAM_COOKIES_FILE": lambda s: s.instagram_cookies_file,
    "MAX_FILE_SIZE": lambda s: s.max_file_size,
    "MAX_FILE_SIZE_MB": lambda s: s.max_file_size_mb,
    "DOWNLOAD_TIMEOUT": lambda s: s.download_timeout,
    "SESSION_TIMEOUT": lambda s: s.session_timeout,
    "DOWNLOAD_SEMAPHORE_LIMIT": lambda s: s.download_semaphore_limit,
    "CLEANUP_INTERVAL": lambda s: s.cleanup_interval,
    "TEMP_FILE_TTL": lambda s: s.temp_file_ttl,
    "TEMP_DIR": lambda s: s.temp_dir,
    "STATS_DB_PATH": lambda s: s.stats_db_path,
    "SUPPORTED_VIDEO_DOMAINS": lambda s: list(s.supported_video_domains),
    "DEFAULT_QUALITIES": lambda s: list(s.default_qualities),
    "STATS_CACHE_TTL": lambda s: s.stats_cache_ttl,
    "LOG_FORMAT": lambda s: s.log_format,
    "LOG_LEVEL": lambda s: s.log_level,
    "USE_LOCAL_BOT_API": lambda s: s.use_local_bot_api,
    "TELEGRAM_API_BASE": lambda s: s.telegram_api_base,
}


def __getattr__(name: str):
    factory = _FACTORIES.get(name)
    if factory is None:
        raise AttributeError(f"module 'config' has no attribute {name!r}")
    from settings import settings
    return factory(settings)
