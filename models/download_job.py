"""
Модели задач скачивания.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal


MediaChoice = Literal["audio", "video"]


@dataclass(frozen=True)
class MediaInfoResult:
    qualities: list[str]
    quality_sizes: dict[str, int]
    fallback_mode: bool
    is_rutube: bool
    title: str | None = None


@dataclass(frozen=True)
class DownloadJob:
    job_id: str
    user_id: int
    url: str
    choice: MediaChoice
    quality: str | None
    is_rutube: bool = False


@dataclass(frozen=True)
class DownloadResult:
    job_id: str
    file_path: Path
    file_size_bytes: int
    title: str
    uploader: str
    media_type: MediaChoice
    quality_label: str
    width: int | None = None
    height: int | None = None
