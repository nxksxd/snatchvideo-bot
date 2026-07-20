"""
Управление временными файлами.
"""

from __future__ import annotations

import asyncio
import shutil
import time
from pathlib import Path


class TempFileService:
    def __init__(self, base_dir: Path, stale_after_seconds: int = 1800):
        self.base_dir = Path(base_dir)
        self.stale_after_seconds = stale_after_seconds

    def ensure_base_dir(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def reset_base_dir(self):
        """
        Синхронный сброс базовой директории. Использовать ТОЛЬКО вне
        event-loop'а (например, в init-скриптах). Внутри корутины
        предпочитайте :meth:`reset_base_dir_async`, чтобы не блокировать loop
        на ``shutil.rmtree`` — после сбоя там может оказаться несколько
        гигабайт незавершённых ``.part``-файлов.
        """
        if self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
        self.ensure_base_dir()

    async def reset_base_dir_async(self) -> None:
        """Неблокирующая версия :meth:`reset_base_dir`."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.reset_base_dir)

    def create_job_dir(self, job_id: str) -> Path:
        self.ensure_base_dir()
        job_dir = self.base_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        return job_dir

    def cleanup_job_dir(self, job_id: str):
        self.cleanup_path(self.base_dir / job_id)

    def cleanup_path(self, path: Path):
        if not path.exists():
            return
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
        else:
            path.unlink(missing_ok=True)

    def cleanup_stale_dirs(self, active_job_ids: set[str]) -> int:
        if not self.base_dir.exists():
            return 0

        now = time.time()
        removed = 0
        for item in self.base_dir.iterdir():
            if item.name in active_job_ids:
                continue
            try:
                if now - item.stat().st_mtime > self.stale_after_seconds:
                    self.cleanup_path(item)
                    removed += 1
            except FileNotFoundError:
                continue
        return removed
