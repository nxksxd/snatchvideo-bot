import tempfile
import unittest
from pathlib import Path

from services.downloader import DownloadManager
from settings import Settings


class _FakeTempFileService:
    def create_job_dir(self, job_id):
        return Path(f"/tmp/{job_id}")

    def cleanup_job_dir(self, job_id):
        return None


def _settings(
    cookies_file: Path | None = None,
    instagram_cookies_file: Path | None = None,
) -> Settings:
    return Settings.for_tests(
        youtube_cookies_file=cookies_file,
        instagram_cookies_file=instagram_cookies_file,
    )


class YoutubeCookiesOptionsTests(unittest.TestCase):
    def test_cookies_attached_for_youtube_when_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"# Netscape HTTP Cookie File\n")
            cookies_path = Path(f.name)
        try:
            manager = DownloadManager(_settings(cookies_path), _FakeTempFileService())
            opts = manager._build_common_options("https://youtu.be/abc")
            self.assertEqual(opts.get("cookiefile"), str(cookies_path))
        finally:
            cookies_path.unlink()

    def test_cookies_not_attached_for_non_youtube(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            cookies_path = Path(f.name)
        try:
            manager = DownloadManager(_settings(cookies_path), _FakeTempFileService())
            opts = manager._build_common_options("https://www.tiktok.com/@user/video/1")
            self.assertNotIn("cookiefile", opts)
        finally:
            cookies_path.unlink()

    def test_cookies_skipped_when_file_missing(self):
        manager = DownloadManager(
            _settings(Path("/nonexistent/cookies.txt")), _FakeTempFileService()
        )
        opts = manager._build_common_options("https://youtube.com/watch?v=x")
        self.assertNotIn("cookiefile", opts)

    def test_cookies_skipped_when_setting_unset(self):
        manager = DownloadManager(_settings(None), _FakeTempFileService())
        opts = manager._build_common_options("https://youtube.com/watch?v=x")
        self.assertNotIn("cookiefile", opts)


class YoutubePlayerClientTests(unittest.TestCase):
    def test_deno_runtime_set_for_youtube(self):
        manager = DownloadManager(_settings(None), _FakeTempFileService())
        opts = manager._build_common_options("https://youtu.be/abc")
        self.assertEqual(
            opts.get("js_runtimes"),
            {"deno": {"path": "/usr/local/bin/deno"}},
        )

    def test_remote_components_ejs_for_youtube(self):
        manager = DownloadManager(_settings(None), _FakeTempFileService())
        opts = manager._build_common_options("https://youtu.be/abc")
        self.assertEqual(opts.get("remote_components"), ["ejs:github"])

    def test_no_extractor_args_for_non_youtube(self):
        manager = DownloadManager(_settings(None), _FakeTempFileService())
        opts = manager._build_common_options("https://www.tiktok.com/@u/video/1")
        self.assertNotIn("extractor_args", opts)
        self.assertNotIn("remote_components", opts)
        opts = manager._build_common_options("https://rutube.ru/video/x")
        self.assertNotIn("extractor_args", opts)
        self.assertNotIn("remote_components", opts)


class InstagramCookiesOptionsTests(unittest.TestCase):
    def test_cookies_attached_for_instagram_when_file_exists(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            f.write(b"# Netscape HTTP Cookie File\n")
            cookies_path = Path(f.name)
        try:
            manager = DownloadManager(
                _settings(instagram_cookies_file=cookies_path), _FakeTempFileService()
            )
            opts = manager._build_common_options(
                "https://www.instagram.com/reel/abc/"
            )
            self.assertEqual(opts.get("cookiefile"), str(cookies_path))
        finally:
            cookies_path.unlink()

    def test_instagram_cookies_not_attached_for_non_instagram(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            cookies_path = Path(f.name)
        try:
            manager = DownloadManager(
                _settings(instagram_cookies_file=cookies_path), _FakeTempFileService()
            )
            opts = manager._build_common_options(
                "https://www.tiktok.com/@user/video/1"
            )
            self.assertNotIn("cookiefile", opts)
            opts = manager._build_common_options("https://youtu.be/abc")
            # YouTube cookies are unset, so cookiefile should NOT be set
            self.assertNotIn("cookiefile", opts)
        finally:
            cookies_path.unlink()

    def test_instagram_cookies_skipped_when_file_missing(self):
        manager = DownloadManager(
            _settings(instagram_cookies_file=Path("/nonexistent/ig.txt")),
            _FakeTempFileService(),
        )
        opts = manager._build_common_options("https://www.instagram.com/reel/abc/")
        self.assertNotIn("cookiefile", opts)

    def test_instagram_cookies_skipped_when_setting_unset(self):
        manager = DownloadManager(_settings(), _FakeTempFileService())
        opts = manager._build_common_options("https://www.instagram.com/reel/abc/")
        self.assertNotIn("cookiefile", opts)


class IsYoutubeUrlTests(unittest.TestCase):
    def test_recognises_youtube_domains(self):
        import utils

        self.assertTrue(utils.is_youtube_url("https://www.youtube.com/watch?v=x"))
        self.assertTrue(utils.is_youtube_url("https://youtu.be/x"))
        self.assertTrue(utils.is_youtube_url("https://m.youtube.com/watch?v=x"))
        self.assertTrue(utils.is_youtube_url("https://music.youtube.com/watch?v=x"))
        self.assertFalse(utils.is_youtube_url("https://www.tiktok.com/@u/video/1"))
        self.assertFalse(utils.is_youtube_url("https://rutube.ru/video/x"))


if __name__ == "__main__":
    unittest.main()
