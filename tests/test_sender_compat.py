import unittest

from services.video_compat import is_ios_compatible_video


class SenderCompatibilityTests(unittest.TestCase):
    def test_h264_aac_yuv420p_is_supported(self):
        self.assertTrue(is_ios_compatible_video("h264", "aac", "yuv420p"))

    def test_hevc_requires_transcode(self):
        self.assertFalse(is_ios_compatible_video("hevc", "aac", "yuv420p"))

    def test_non_aac_audio_requires_transcode(self):
        self.assertFalse(is_ios_compatible_video("h264", "opus", "yuv420p"))

    def test_non_yuv420p_requires_transcode(self):
        self.assertFalse(is_ios_compatible_video("h264", "aac", "yuvj420p"))


if __name__ == "__main__":
    unittest.main()
