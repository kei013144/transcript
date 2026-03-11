"""Audio cache handling and YouTube audio download."""

from __future__ import annotations

import logging
from pathlib import Path
from shutil import which

import yt_dlp

from .exceptions import AudioDownloadError


class AudioCacheManager:
    """Manage cached audio files keyed by YouTube video_id."""

    def __init__(self, output_root: Path, logger: logging.Logger | None = None) -> None:
        self.output_root = output_root
        self.youtube_root = self.output_root / "youtube"
        self.logger = logger or logging.getLogger(__name__)

    def video_root(self, video_id: str) -> Path:
        return self.youtube_root / video_id

    def audio_dir(self, video_id: str) -> Path:
        return self.video_root(video_id) / "audio"

    def audio_path(self, video_id: str) -> Path:
        return self.audio_dir(video_id) / "source.m4a"

    def transcript_dir(self, video_id: str) -> Path:
        return self.video_root(video_id) / "transcript"

    def ensure_video_dirs(self, video_id: str) -> None:
        self.audio_dir(video_id).mkdir(parents=True, exist_ok=True)
        self.transcript_dir(video_id).mkdir(parents=True, exist_ok=True)

    def has_audio_cache(self, video_id: str) -> bool:
        return self.audio_path(video_id).exists()

    def get_or_download_audio(
        self, url: str, video_id: str, force_download: bool = False
    ) -> tuple[Path, bool]:
        """
        Return cached audio when available.

        Returns:
            tuple[path, downloaded_now]
        """
        self.ensure_video_dirs(video_id)
        target_path = self.audio_path(video_id)

        if target_path.exists() and not force_download:
            self.logger.info("Audio cache hit: %s", target_path)
            return target_path, False

        if force_download and target_path.exists():
            target_path.unlink(missing_ok=True)

        self.logger.info("Downloading audio with yt-dlp for video_id=%s", video_id)
        if which("ffmpeg") is None:
            raise AudioDownloadError(
                "ffmpeg not found in PATH. Install ffmpeg before downloading audio."
            )

        outtmpl = str(self.audio_dir(video_id) / "source.%(ext)s")
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "m4a",
                    "preferredquality": "192",
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as exc:  # pragma: no cover - external dependency errors
            raise AudioDownloadError(
                "Audio download failed. Ensure yt-dlp and ffmpeg are installed."
            ) from exc

        if target_path.exists():
            return target_path, True

        candidates = sorted(self.audio_dir(video_id).glob("source.*"))
        if len(candidates) == 1 and candidates[0].suffix.lower() == ".m4a":
            candidates[0].replace(target_path)
            return target_path, True

        raise AudioDownloadError(
            f"Download completed but expected audio file was not found: {target_path}"
        )
