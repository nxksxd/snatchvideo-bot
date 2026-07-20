import unittest

from services.media_info import build_media_info_result


class MediaInfoTests(unittest.TestCase):
    def test_build_quality_sizes(self):
        info = {
            "title": "Video",
            "formats": [
                {"height": 720, "vcodec": "avc1", "filesize": 400},
                {"height": 720, "vcodec": "avc1", "filesize": 500},
                {"height": None, "vcodec": "none", "acodec": "mp4a", "filesize": 100},
            ],
        }
        result = build_media_info_result(
            "https://youtube.com/watch?v=1",
            info,
            ("1080", "720", "480", "360"),
        )
        self.assertEqual(result.qualities, ["720"])
        self.assertEqual(result.quality_sizes["720"], 600)
        self.assertFalse(result.fallback_mode)

    def test_rutube_fallback(self):
        result = build_media_info_result(
            "https://rutube.ru/video/test",
            None,
            ("1080", "720", "480", "360"),
        )
        self.assertTrue(result.is_rutube)
        self.assertTrue(result.fallback_mode)


if __name__ == "__main__":
    unittest.main()
