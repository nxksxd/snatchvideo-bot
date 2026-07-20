"""
Репозиторий статистики загрузок.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class StatsRepository:
    """Работа со статистикой загрузок через SQLite."""

    def __init__(self, db_path: Path, cache_ttl: int = 300):
        self.db_path = Path(db_path)
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[Any, float]] = {}
        self._cache_lock = threading.Lock()

    @contextmanager
    def _get_connection(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=5000")
        try:
            yield conn
        finally:
            conn.close()

    def _invalidate_cache(self):
        with self._cache_lock:
            self._cache.clear()

    def _get_cached(self, key: str) -> Any | None:
        with self._cache_lock:
            cached = self._cache.get(key)
            if not cached:
                return None

            value, timestamp = cached
            if time.time() - timestamp < self.cache_ttl:
                return value

            self._cache.pop(key, None)
            return None

    def _set_cached(self, key: str, value: Any):
        with self._cache_lock:
            self._cache[key] = (value, time.time())

    def init_db(self):
        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS downloads (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER NOT NULL,
                    username    TEXT,
                    first_name  TEXT,
                    last_name   TEXT,
                    domain      TEXT NOT NULL,
                    media_type  TEXT NOT NULL,
                    quality     TEXT,
                    file_size   INTEGER DEFAULT 0,
                    url         TEXT,
                    title       TEXT,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_downloads_domain ON downloads(domain)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_downloads_created ON downloads(created_at)")
            conn.commit()

        logger.info("📊 База статистики инициализирована: %s", self.db_path)

    def record_download(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        domain: str,
        media_type: str,
        quality: str | None,
        file_size: int = 0,
        url: str = "",
        title: str = "",
    ) -> bool:
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO downloads
                        (user_id, username, first_name, last_name, domain,
                         media_type, quality, file_size, url, title)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user_id,
                        username,
                        first_name,
                        last_name,
                        domain,
                        media_type,
                        quality,
                        file_size,
                        url,
                        title,
                    ),
                )
                conn.commit()
        except Exception:
            logger.exception("Ошибка записи статистики")
            return False

        self._invalidate_cache()
        return True

    def get_global_stats(self) -> dict[str, Any]:
        cache_key = "global_stats"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM downloads")
            total_downloads = c.fetchone()[0]

            c.execute("SELECT COUNT(DISTINCT user_id) FROM downloads")
            unique_users = c.fetchone()[0]

            c.execute(
                """
                SELECT domain, COUNT(*) as cnt
                FROM downloads
                GROUP BY domain
                ORDER BY cnt DESC
                """
            )
            by_domain = [tuple(row) for row in c.fetchall()]

            c.execute(
                """
                SELECT media_type, COUNT(*) as cnt
                FROM downloads
                GROUP BY media_type
                ORDER BY cnt DESC
                """
            )
            by_type = [tuple(row) for row in c.fetchall()]

            c.execute(
                """
                SELECT quality, COUNT(*) as cnt
                FROM downloads
                WHERE media_type = 'video' AND quality IS NOT NULL
                GROUP BY quality
                ORDER BY cnt DESC
                """
            )
            by_quality = [tuple(row) for row in c.fetchall()]

            c.execute(
                """
                SELECT user_id, username, first_name, last_name, COUNT(*) as cnt
                FROM downloads
                GROUP BY user_id
                ORDER BY cnt DESC
                LIMIT 10
                """
            )
            top_users = [tuple(row) for row in c.fetchall()]

            today_str = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT COUNT(*) FROM downloads WHERE DATE(created_at) = ?", (today_str,))
            today_downloads = c.fetchone()[0]

            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            c.execute("SELECT COUNT(*) FROM downloads WHERE DATE(created_at) >= ?", (week_ago,))
            week_downloads = c.fetchone()[0]

            month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            c.execute("SELECT COUNT(*) FROM downloads WHERE DATE(created_at) >= ?", (month_ago,))
            month_downloads = c.fetchone()[0]

            c.execute("SELECT COALESCE(SUM(file_size), 0) FROM downloads")
            total_bytes = c.fetchone()[0]

        stats = {
            "total_downloads": total_downloads,
            "unique_users": unique_users,
            "by_domain": by_domain,
            "by_type": by_type,
            "by_quality": by_quality,
            "top_users": top_users,
            "today_downloads": today_downloads,
            "week_downloads": week_downloads,
            "month_downloads": month_downloads,
            "total_bytes": total_bytes,
        }
        self._set_cached(cache_key, stats)
        return stats

    def get_user_stats(self, user_id: int) -> dict[str, Any]:
        cache_key = f"user_stats_{user_id}"
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        with self._get_connection() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM downloads WHERE user_id = ?", (user_id,))
            total = c.fetchone()[0]

            c.execute(
                """
                SELECT domain, COUNT(*) as cnt
                FROM downloads
                WHERE user_id = ?
                GROUP BY domain
                ORDER BY cnt DESC
                """,
                (user_id,),
            )
            by_domain = [tuple(row) for row in c.fetchall()]

            c.execute(
                """
                SELECT media_type, COUNT(*) as cnt
                FROM downloads
                WHERE user_id = ?
                GROUP BY media_type
                ORDER BY cnt DESC
                """,
                (user_id,),
            )
            by_type = [tuple(row) for row in c.fetchall()]

            c.execute(
                "SELECT COALESCE(SUM(file_size), 0) FROM downloads WHERE user_id = ?",
                (user_id,),
            )
            total_bytes = c.fetchone()[0]

            c.execute("SELECT MIN(created_at) FROM downloads WHERE user_id = ?", (user_id,))
            first_download = c.fetchone()[0]

            c.execute("SELECT MAX(created_at) FROM downloads WHERE user_id = ?", (user_id,))
            last_download = c.fetchone()[0]

        stats = {
            "total": total,
            "by_domain": by_domain,
            "by_type": by_type,
            "total_bytes": total_bytes,
            "first_download": first_download,
            "last_download": last_download,
        }
        self._set_cached(cache_key, stats)
        return stats
