"""Orchestration logic for the transcript generation pipeline."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .audio_cache_manager import AudioCacheManager
from .models import TranscriptResult, VideoMetadata
from .transcriber import Transcriber
from .transcript_store import TranscriptStore
from .youtube_resolver import YouTubeResolver


class TranscriptService:
    """Run end-to-end workflow from URL to stored transcript files."""

    def __init__(
        self,
        resolver: YouTubeResolver,
        audio_cache: AudioCacheManager,
        transcript_store: TranscriptStore,
        transcriber_factory: Callable[[], Transcriber],
        logger: logging.Logger | None = None,
    ) -> None:
        self.resolver = resolver
        self.audio_cache = audio_cache
        self.transcript_store = transcript_store
        self._transcriber_factory = transcriber_factory
        self._transcriber: Transcriber | None = None
        self.logger = logger or logging.getLogger(__name__)

    def run(
        self,
        url: str,
        force_download: bool = False,
        force_transcribe: bool = False,
        prefer_captions: bool = False,
    ) -> dict[str, str]:
        video_id = self.resolver.extract_video_id(url)
        video = self.resolver.fetch_metadata(url)

        if video.video_id != video_id:
            self.logger.info(
                "Resolved metadata video_id differs from URL video_id: %s -> %s",
                video_id,
                video.video_id,
            )
            video_id = video.video_id

        audio_path, audio_downloaded_now = self.audio_cache.get_or_download_audio(
            url=url, video_id=video_id, force_download=force_download
        )

        transcript_path = self.transcript_store.transcript_path(video_id)
        segments_path = self.transcript_store.segments_path(video_id)
        metadata_path = self.transcript_store.metadata_path(video_id)

        transcript_cached = (
            self.transcript_store.has_transcript_cache(video_id) and not force_transcribe
        )

        if transcript_cached:
            self.logger.info("Transcript cache hit: %s", transcript_path)
            if not metadata_path.exists():
                self.transcript_store.save_metadata(
                    video_id=video_id,
                    metadata=self._build_metadata(
                        video=video,
                        audio_path=audio_path,
                        transcript_path=transcript_path,
                        segments_path=segments_path,
                        source="cache",
                        transcript_cached=True,
                        audio_cached=not audio_downloaded_now,
                    ),
                )
        else:
            transcript_result = self._transcribe_with_fallback(
                audio_path=audio_path,
                language=video.language,
                prefer_captions=prefer_captions,
            )
            full_text = _build_full_text(transcript_result)
            self.transcript_store.save_transcript(
                video_id=video_id,
                transcript_text=full_text,
                segments=transcript_result.segments,
                metadata=self._build_metadata(
                    video=video,
                    audio_path=audio_path,
                    transcript_path=transcript_path,
                    segments_path=segments_path,
                    source=transcript_result.source,
                    transcript_cached=False,
                    audio_cached=not audio_downloaded_now,
                    language_override=transcript_result.language,
                ),
            )

        return {
            "video_id": video_id,
            "audio_path": str(audio_path.resolve()),
            "transcript_path": str(transcript_path.resolve()),
            "segments_path": str(segments_path.resolve()),
            "metadata_path": str(metadata_path.resolve()),
        }

    def _transcribe_with_fallback(
        self, audio_path: Path, language: str | None, prefer_captions: bool
    ) -> TranscriptResult:
        if prefer_captions:
            self.logger.info(
                "--prefer-captions is enabled, but caption-based transcript is not implemented yet. Falling back to speech-to-text."
            )
        return self._get_transcriber().transcribe(
            audio_path=audio_path, language=language
        )

    def _get_transcriber(self) -> Transcriber:
        if self._transcriber is None:
            self._transcriber = self._transcriber_factory()
        return self._transcriber

    @staticmethod
    def _build_metadata(
        video: VideoMetadata,
        audio_path: Path,
        transcript_path: Path,
        segments_path: Path,
        source: str,
        transcript_cached: bool,
        audio_cached: bool,
        language_override: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "video_id": video.video_id,
            "original_url": video.original_url,
            "title": video.title,
            "duration": video.duration,
            "uploader": video.uploader,
            "upload_date": video.upload_date,
            "language": language_override or video.language,
            "created_at": now,
            "audio_path": str(audio_path.resolve()),
            "transcript_path": str(transcript_path.resolve()),
            "segments_path": str(segments_path.resolve()),
            "source": source,
            "cache": {
                "audio_cached": audio_cached,
                "transcript_cached": transcript_cached,
            },
        }


def _build_full_text(result: TranscriptResult) -> str:
    if result.segments:
        joined = "\n".join(segment.text.strip() for segment in result.segments).strip()
        if joined:
            return joined
    return result.text.strip()
