import unittest
from pathlib import Path

from models import DownloadResult
from services.sender import MediaSender


def _make_result(*, title: str, uploader: str = "channel") -> DownloadResult:
    return DownloadResult(
        job_id="job",
        file_path=Path("/tmp/x.mp4"),
        file_size_bytes=1,
        title=title,
        uploader=uploader,
        media_type="video",
        quality_label="720p",
        width=1280,
        height=720,
    )


class CaptionEscapingTests(unittest.TestCase):
    def setUp(self):
        self.sender = MediaSender()

    def test_url_with_quote_is_escaped(self):
        result = _make_result(title="Sample")
        caption = self.sender._build_caption(
            result, 'https://example.com/path?q="evil"'
        )
        self.assertNotIn('"evil"', caption)
        self.assertIn("&quot;evil&quot;", caption)

    def test_url_with_ampersand_is_escaped(self):
        result = _make_result(title="Sample")
        caption = self.sender._build_caption(
            result, "https://example.com/?a=1&b=2"
        )
        self.assertIn("a=1&amp;b=2", caption)

    def test_title_with_html_is_escaped(self):
        result = _make_result(title="<script>alert(1)</script>")
        caption = self.sender._build_caption(result, "https://example.com/")
        self.assertNotIn("<script>", caption)
        self.assertIn("&lt;script&gt;", caption)


if __name__ == "__main__":
    unittest.main()
