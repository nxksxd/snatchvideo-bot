import asyncio
import unittest
from pathlib import Path

from models import DownloadJob
from services.downloader import (
    ActiveDownloadHandle,
    DownloadAlreadyInProgress,
    DownloadManager,
)


class _FakeTempFileService:
    def create_job_dir(self, job_id):
        return Path(f"/tmp/{job_id}")

    def cleanup_job_dir(self, job_id):
        return None


def _make_settings():
    from settings import Settings

    return Settings.for_tests()


class DownloadManagerConcurrencyTests(unittest.TestCase):
    def test_second_download_for_same_user_raises(self):
        async def run():
            manager = DownloadManager(_make_settings(), _FakeTempFileService())
            handle = ActiveDownloadHandle(user_id=42, job_id="job-1")
            async with manager._lock:
                manager._active_by_user[42] = handle

            job = DownloadJob(
                job_id="job-2",
                user_id=42,
                url="https://example.com/v",
                choice="video",
                quality="720",
            )

            with self.assertRaises(DownloadAlreadyInProgress):
                await manager.download(job)

        asyncio.run(run())

    def test_different_users_are_independent(self):
        async def run():
            manager = DownloadManager(_make_settings(), _FakeTempFileService())
            async with manager._lock:
                manager._active_by_user[1] = ActiveDownloadHandle(user_id=1, job_id="a")

            self.assertIn(1, manager._active_by_user)
            self.assertNotIn(2, manager._active_by_user)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
