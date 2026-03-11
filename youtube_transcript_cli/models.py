"""Data models used by the transcript CLI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Segment:
    """One transcription segment with timing and text."""

    start: float
    end: float
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {"start": self.start, "end": self.end, "text": self.text}


@dataclass(slots=True)
class TranscriptResult:
    """Transcription output from an engine."""

    text: str
    segments: list[Segment]
    language: str | None = None
    source: str = "openai"


@dataclass(slots=True)
class VideoMetadata:
    """YouTube metadata fetched from yt-dlp."""

    video_id: str
    original_url: str
    title: str | None
    duration: int | None
    uploader: str | None
    upload_date: str | None
    language: str | None

