"""
Подготовка информации о доступных качествах.
"""

from __future__ import annotations

from models import MediaInfoResult

import utils


def build_media_info_result(
    url: str,
    info: dict | None,
    default_qualities: tuple[str, ...],
) -> MediaInfoResult:
    is_rutube = utils.is_rutube_url(url)
    title = info.get("title") if info else None

    if is_rutube:
        return MediaInfoResult(
            qualities=list(default_qualities),
            quality_sizes={},
            fallback_mode=True,
            is_rutube=True,
            title=title,
        )

    if not info or not info.get("formats") or len(info.get("formats", [])) < 2:
        return MediaInfoResult(
            qualities=list(default_qualities),
            quality_sizes={},
            fallback_mode=True,
            is_rutube=False,
            title=title,
        )

    formats = info.get("formats", [])
    audio_formats = [
        item
        for item in formats
        if item.get("acodec") not in (None, "none") and item.get("vcodec") in (None, "none")
    ]

    best_audio_size = 0
    if audio_formats:
        best_audio = max(
            audio_formats,
            key=lambda item: item.get("filesize") or item.get("filesize_approx") or 0,
        )
        best_audio_size = best_audio.get("filesize") or best_audio.get("filesize_approx") or 0

    quality_data: dict[str, int] = {}
    for item in formats:
        height = item.get("height")
        if not height or height < 144 or item.get("vcodec") in (None, "none"):
            continue

        quality = str(height)
        file_size = item.get("filesize") or item.get("filesize_approx") or 0
        if quality not in quality_data or file_size > quality_data[quality]:
            quality_data[quality] = file_size

    if not quality_data:
        return MediaInfoResult(
            qualities=list(default_qualities),
            quality_sizes={},
            fallback_mode=True,
            is_rutube=False,
            title=title,
        )

    sorted_qualities = sorted(quality_data.keys(), key=int, reverse=True)
    quality_sizes = {quality: quality_data[quality] + best_audio_size for quality in sorted_qualities}
    return MediaInfoResult(
        qualities=sorted_qualities,
        quality_sizes=quality_sizes,
        fallback_mode=False,
        is_rutube=False,
        title=title,
    )
