import unittest

import utils


class UtilsTests(unittest.TestCase):
    def test_normalize_url_adds_scheme(self):
        self.assertEqual(
            utils.normalize_url("youtube.com/watch?v=123"),
            "https://youtube.com/watch?v=123",
        )

    def test_supported_url(self):
        self.assertTrue(utils.is_supported_url("https://www.youtube.com/watch?v=abc"))
        self.assertFalse(utils.is_supported_url("https://example.com/video"))

    def test_format_bytes(self):
        self.assertEqual(utils.format_bytes(512), "512 Б")
        self.assertEqual(utils.format_bytes(1024), "1.0 КБ")

    def test_escape_html(self):
        self.assertEqual(utils.escape_html("<b>x</b>"), "&lt;b&gt;x&lt;/b&gt;")


if __name__ == "__main__":
    unittest.main()
