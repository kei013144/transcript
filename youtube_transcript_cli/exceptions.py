"""Custom exception types for the transcript CLI."""


class TranscriptCliError(Exception):
    """Base exception for all CLI related failures."""


class InvalidYouTubeUrlError(TranscriptCliError):
    """Raised when a URL cannot be parsed as a valid YouTube URL."""


class VideoMetadataFetchError(TranscriptCliError):
    """Raised when video metadata cannot be fetched."""


class AudioDownloadError(TranscriptCliError):
    """Raised when audio download or conversion fails."""


class TranscriptionError(TranscriptCliError):
    """Raised when transcription fails."""

