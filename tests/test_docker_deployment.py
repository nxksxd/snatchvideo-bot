"""Production Docker deployment contract."""

import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class DockerDeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.compose = (ROOT / "compose.yml").read_text()
        cls.dockerfile = (ROOT / "Dockerfile").read_text()

    def test_video_bot_has_hard_resource_limits(self):
        self.assertIn("cpus: 2.0", self.compose)
        self.assertIn("mem_limit: 4g", self.compose)
        self.assertIn("pids_limit: 512", self.compose)

    def test_video_bot_uses_three_download_slots_and_2000_mb_limit(self):
        self.assertIn("DOWNLOAD_SEMAPHORE_LIMIT: 3", self.compose)
        self.assertIn("MAX_FILE_SIZE_MB: 2000", self.compose)

    def test_services_are_private_and_persistent(self):
        self.assertNotIn("ports:", self.compose)
        self.assertIn("video-temp:/var/lib/snatchvideo-bot/tmp", self.compose)
        self.assertIn("video-data:/var/lib/snatchvideo-bot", self.compose)
        self.assertIn("telegram-api-data:/var/lib/telegram-bot-api", self.compose)

    def test_image_contains_media_dependencies_and_runs_non_root(self):
        self.assertIn("ffmpeg", self.dockerfile)
        self.assertIn("deno", self.dockerfile)
        self.assertIn("USER bot", self.dockerfile)


if __name__ == "__main__":
    unittest.main()
