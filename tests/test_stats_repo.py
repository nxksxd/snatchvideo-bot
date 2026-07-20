import tempfile
import unittest
from pathlib import Path

from repositories.stats_repo import StatsRepository


class StatsRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "stats.db"
        self.repo = StatsRepository(self.db_path, cache_ttl=1)
        self.repo.init_db()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_record_and_fetch_user_stats(self):
        self.assertTrue(
            self.repo.record_download(
                user_id=1,
                username="tester",
                first_name="Test",
                last_name=None,
                domain="YouTube",
                media_type="video",
                quality="720p",
                file_size=1024,
                url="https://youtube.com/watch?v=1",
                title="Sample",
            )
        )

        stats = self.repo.get_user_stats(1)
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["total_bytes"], 1024)

    def test_global_stats(self):
        self.repo.record_download(1, "u1", "A", None, "YouTube", "video", "720p", 100, "", "")
        self.repo.record_download(2, "u2", "B", None, "VK", "audio", "MP3", 200, "", "")

        stats = self.repo.get_global_stats()
        self.assertEqual(stats["total_downloads"], 2)
        self.assertEqual(stats["unique_users"], 2)


if __name__ == "__main__":
    unittest.main()
