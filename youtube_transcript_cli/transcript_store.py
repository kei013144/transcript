"""Persistence for transcript artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import Segment


class TranscriptStore:
    """Read/write transcript artifacts under data/youtube/<video_id>/transcript."""

    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root
        self.youtube_root = output_root / "youtube"

    def video_root(self, video_id: str) -> Path:
        return self.youtube_root / video_id

    def transcript_dir(self, video_id: str) -> Path:
        return self.video_root(video_id) / "transcript"

    def transcript_path(self, video_id: str) -> Path:
        return self.transcript_dir(video_id) / "transcript.txt"

    def segments_path(self, video_id: str) -> Path:
        return self.transcript_dir(video_id) / "segments.json"

    def metadata_path(self, video_id: str) -> Path:
        return self.transcript_dir(video_id) / "metadata.json"

    def ensure_dirs(self, video_id: str) -> None:
        self.transcript_dir(video_id).mkdir(parents=True, exist_ok=True)

    def has_transcript_cache(self, video_id: str) -> bool:
        return self.transcript_path(video_id).exists() and self.segments_path(
            video_id
        ).exists()

    def save_transcript(
        self,
        video_id: str,
        transcript_text: str,
        segments: list[Segment],
        metadata: dict[str, Any],
    ) -> None:
        self.ensure_dirs(video_id)

        transcript_path = self.transcript_path(video_id)
        segments_path = self.segments_path(video_id)
        metadata_path = self.metadata_path(video_id)

        transcript_path.write_text(transcript_text.strip() + "\n", encoding="utf-8")
        segments_payload = [segment.to_dict() for segment in segments]
        segments_path.write_text(
            json.dumps(segments_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        metadata_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def save_metadata(self, video_id: str, metadata: dict[str, Any]) -> None:
        self.ensure_dirs(video_id)
        self.metadata_path(video_id).write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def read_metadata(self, video_id: str) -> dict[str, Any] | None:
        metadata_path = self.metadata_path(video_id)
        if not metadata_path.exists():
            return None
        return json.loads(metadata_path.read_text(encoding="utf-8"))

