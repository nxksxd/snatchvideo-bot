"""
Проверка совместимости видео для iOS.
"""

from __future__ import annotations


def is_ios_compatible_video(
    video_codec: str | None,
    audio_codec: str | None,
    pix_fmt: str | None,
) -> bool:
    """Проверяет, подходит ли видео для надежного воспроизведения на iOS."""
    if video_codec != "h264":
        return False
    if pix_fmt != "yuv420p":
        return False
    if audio_codec not in (None, "aac"):
        return False
    return True
