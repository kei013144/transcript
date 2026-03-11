"""YouTube URL parsing and metadata resolution."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

import yt_dlp

from .exceptions import InvalidYouTubeUrlError, VideoMetadataFetchError
from .models import VideoMetadata


class YouTubeResolver:
    """Resolve YouTube URL details and fetch metadata."""

    _VIDEO_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{11}$")
    _FALLBACK_ID_PATTERN = re.compile(r"(?:v=|/)([0-9A-Za-z_-]{11})(?:[?&#/]|$)")

    def extract_video_id(self, url: str) -> str:
        """Extract YouTube video ID from a URL."""
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidYouTubeUrlError(f"Invalid URL format: {url}")

        host = parsed.netloc.lower()
        if not self._is_supported_host(host):
            raise InvalidYouTubeUrlError(f"Unsupported YouTube domain: {parsed.netloc}")

        candidates: list[str] = []

        if self._is_short_domain(host):
            short_id = parsed.path.lstrip("/").split("/", maxsplit=1)[0]
            if short_id:
                candidates.append(short_id)

        if self._is_main_domain(host):
            query = parse_qs(parsed.query)
            if "v" in query and query["v"]:
                candidates.append(query["v"][0])

            path_parts = [part for part in parsed.path.split("/") if part]
            markers = {"shorts", "embed", "live", "v"}
            for i, part in enumerate(path_parts):
                if part in markers and i + 1 < len(path_parts):
                    candidates.append(path_parts[i + 1])

        fallback_match = self._FALLBACK_ID_PATTERN.search(url)
        if fallback_match:
            candidates.append(fallback_match.group(1))

        for candidate in candidates:
            if self._VIDEO_ID_PATTERN.fullmatch(candidate):
                return candidate

        raise InvalidYouTubeUrlError(
            f"Could not extract a valid YouTube video_id from URL: {url}"
        )

    def fetch_metadata(self, url: str) -> VideoMetadata:
        """Fetch video metadata with yt-dlp without downloading media."""
        video_id = self.extract_video_id(url)
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
        except Exception as exc:  # pragma: no cover - external dependency errors
            raise VideoMetadataFetchError(
                f"Failed to fetch video metadata for {url}"
            ) from exc

        if not isinstance(info, dict):
            raise VideoMetadataFetchError(f"Unexpected metadata format for {url}")

        resolved_id = str(info.get("id") or video_id)
        upload_date = self._normalize_upload_date(info.get("upload_date"))

        duration = info.get("duration")
        parsed_duration = int(duration) if isinstance(duration, (int, float)) else None

        language = info.get("language")
        if isinstance(language, str):
            normalized_language = language
        else:
            normalized_language = None

        return VideoMetadata(
            video_id=resolved_id,
            original_url=url,
            title=_as_optional_str(info.get("title")),
            duration=parsed_duration,
            uploader=_as_optional_str(info.get("uploader")),
            upload_date=upload_date,
            language=normalized_language,
        )

    @staticmethod
    def _normalize_upload_date(value: object) -> str | None:
        """Convert YYYYMMDD into YYYY-MM-DD when possible."""
        if not isinstance(value, str) or len(value) != 8 or not value.isdigit():
            return _as_optional_str(value)
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"

    @staticmethod
    def _is_short_domain(host: str) -> bool:
        return host == "youtu.be" or host.endswith(".youtu.be")

    @staticmethod
    def _is_main_domain(host: str) -> bool:
        if host == "youtube.com" or host.endswith(".youtube.com"):
            return True
        if host == "youtube-nocookie.com" or host.endswith(".youtube-nocookie.com"):
            return True
        return False

    @classmethod
    def _is_supported_host(cls, host: str) -> bool:
        return cls._is_short_domain(host) or cls._is_main_domain(host)


def _as_optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None
