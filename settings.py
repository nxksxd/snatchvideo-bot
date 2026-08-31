"""
Безопасная загрузка настроек приложения.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from urllib.parse import urlsplit, urlunsplit

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - fallback для окружений без зависимостей
    def load_dotenv(*args, **kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"❌ Обязательная переменная окружения {name} не установлена.")
    return value


def _parse_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"❌ Переменная {name} должна быть целым числом.") from exc


def _mask_proxy(proxy: str | None) -> str | None:
    if not proxy:
        return None

    parts = urlsplit(proxy)
    if not parts.hostname:
        return "***"

    auth = ""
    if parts.username:
        auth = f"{parts.username}:***@"

    host = parts.hostname
    if parts.port:
        host = f"{host}:{parts.port}"

    return urlunsplit((parts.scheme, f"{auth}{host}", parts.path, parts.query, parts.fragment))


_DEFAULT_SUPPORTED_VIDEO_DOMAINS: tuple[str, ...] = (
    "youtube.com",
    "youtu.be",
    "rutube.ru",
    "vk.com",
    "vk.ru",
    "vkvideo.ru",
    "instagram.com",
    "www.instagram.com",
    "tiktok.com",
    "www.tiktok.com",
    "vm.tiktok.com",
    "vt.tiktok.com",
)
_DEFAULT_QUALITIES: tuple[str, ...] = ("1080", "720", "480", "360")


@dataclass(frozen=True)
class Settings:
    token: str
    admin_id: int
    rutube_proxy: str | None
    youtube_proxy: str | None
    youtube_cookies_file: Path | None
    instagram_cookies_file: Path | None
    max_file_size: int
    download_timeout: int
    slow_download_speed: int
    slow_download_window: int
    session_timeout: int
    download_semaphore_limit: int
    cleanup_interval: int
    temp_file_ttl: int
    temp_dir: Path
    stats_db_path: Path
    stats_cache_ttl: int
    supported_video_domains: tuple[str, ...]
    default_qualities: tuple[str, ...]
    log_format: str
    log_level: str
    use_local_bot_api: bool
    telegram_api_base: str | None

    @property
    def masked_proxy(self) -> str | None:
        return _mask_proxy(self.rutube_proxy)

    @property
    def max_file_size_mb(self) -> int:
        return self.max_file_size // 1024 // 1024

    @classmethod
    def for_tests(cls, **overrides) -> "Settings":
        """Сконструировать Settings с дефолтами без чтения env. Для тестов."""
        defaults: dict = dict(
            token="test-token",
            admin_id=0,
            rutube_proxy=None,
            youtube_proxy=None,
            youtube_cookies_file=None,
            instagram_cookies_file=None,
            max_file_size=2000 * 1024 * 1024,
            download_timeout=600,
            slow_download_speed=100 * 1024,
            slow_download_window=45,
            session_timeout=1200,
            download_semaphore_limit=3,
            cleanup_interval=30 * 60,
            temp_file_ttl=30 * 60,
            temp_dir=Path(gettempdir()) / "video_download_bot",
            stats_db_path=BASE_DIR / "stats.db",
            stats_cache_ttl=300,
            supported_video_domains=_DEFAULT_SUPPORTED_VIDEO_DOMAINS,
            default_qualities=_DEFAULT_QUALITIES,
            log_format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            log_level="INFO",
            use_local_bot_api=False,
            telegram_api_base=None,
        )
        defaults.update(overrides)
        return cls(**defaults)

    @classmethod
    def from_env(cls) -> "Settings":
        use_local_bot_api = _parse_bool(os.getenv("USE_LOCAL_BOT_API"), default=False)
        telegram_api_base = os.getenv("TELEGRAM_API_BASE", "").strip() or None
        if use_local_bot_api and not telegram_api_base:
            telegram_api_base = "http://localhost:8081"

        temp_dir_raw = os.getenv("TEMP_DIR", "").strip()
        temp_dir = Path(temp_dir_raw) if temp_dir_raw else Path(gettempdir()) / "video_download_bot"

        stats_db_raw = os.getenv("STATS_DB_PATH", "").strip()
        stats_db_path = Path(stats_db_raw) if stats_db_raw else BASE_DIR / "stats.db"

        cookies_raw = os.getenv("YOUTUBE_COOKIES_FILE", "").strip()
        youtube_cookies_file = Path(cookies_raw) if cookies_raw else None

        ig_cookies_raw = os.getenv("INSTAGRAM_COOKIES_FILE", "").strip()
        instagram_cookies_file = Path(ig_cookies_raw) if ig_cookies_raw else None

        return cls(
            token=_require_env("TELEGRAM_BOT_TOKEN"),
            admin_id=_parse_int("ADMIN_ID", 0),
            rutube_proxy=os.getenv("RUTUBE_PROXY", "").strip() or None,
            youtube_proxy=os.getenv("YOUTUBE_PROXY", "").strip() or None,
            youtube_cookies_file=youtube_cookies_file,
            instagram_cookies_file=instagram_cookies_file,
            max_file_size=_parse_int("MAX_FILE_SIZE_MB", 2000) * 1024 * 1024,
            download_timeout=_parse_int("DOWNLOAD_TIMEOUT", 600),
            slow_download_speed=_parse_int("SLOW_DOWNLOAD_SPEED", 100 * 1024),
            slow_download_window=_parse_int("SLOW_DOWNLOAD_WINDOW", 45),
            session_timeout=_parse_int("SESSION_TIMEOUT", 1200),
            download_semaphore_limit=_parse_int("DOWNLOAD_SEMAPHORE_LIMIT", 3),
            cleanup_interval=_parse_int("CLEANUP_INTERVAL", 30 * 60),
            temp_file_ttl=_parse_int("TEMP_FILE_TTL", 30 * 60),
            temp_dir=temp_dir,
            stats_db_path=stats_db_path,
            stats_cache_ttl=_parse_int("STATS_CACHE_TTL", 300),
            supported_video_domains=(
                "youtube.com",
                "youtu.be",
                "rutube.ru",
                "vk.com",
                "vk.ru",
                "vkvideo.ru",
                "instagram.com",
                "www.instagram.com",
                "tiktok.com",
                "www.tiktok.com",
                "vm.tiktok.com",
                "vt.tiktok.com",
            ),
            default_qualities=("1080", "720", "480", "360"),
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            use_local_bot_api=use_local_bot_api,
            telegram_api_base=telegram_api_base,
        )


_settings_instance: Settings | None = None


def __getattr__(name: str) -> "Settings":
    """
    Ленивая инициализация ``settings`` на уровне модуля (PEP 562).

    Это значит, что просто ``from settings import Settings`` (или любой импорт
    модуля без обращения к ``settings``) не вызывает ``Settings.from_env()`` и
    не требует наличия ``TELEGRAM_BOT_TOKEN`` в окружении. Только реальный
    доступ к ``settings.X`` триггерит загрузку.
    """
    if name == "settings":
        global _settings_instance
        if _settings_instance is None:
            _settings_instance = Settings.from_env()
        return _settings_instance
    raise AttributeError(f"module 'settings' has no attribute {name!r}")
