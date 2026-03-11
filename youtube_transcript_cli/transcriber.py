"""Transcriber interface and backend implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .exceptions import TranscriptionError
from .models import Segment, TranscriptResult


class Transcriber(ABC):
    """Abstract transcriber interface for pluggable backends."""

    @abstractmethod
    def transcribe(
        self, audio_path: Path, language: str | None = None
    ) -> TranscriptResult:
        """Transcribe an audio file into text segments."""


class OpenAITranscriber(Transcriber):
    """OpenAI Speech-to-Text implementation."""

    def __init__(self, model: str = "whisper-1", client: Any | None = None) -> None:
        self.model = model
        self.client = client

    def transcribe(
        self, audio_path: Path, language: str | None = None
    ) -> TranscriptResult:
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file does not exist: {audio_path}")

        request: dict[str, Any] = {
            "model": self.model,
            "response_format": "verbose_json",
            "timestamp_granularities": ["segment"],
            "file": None,
        }
        if language:
            request["language"] = language

        try:
            with audio_path.open("rb") as audio_file:
                request["file"] = audio_file
                response = self._get_client().audio.transcriptions.create(**request)
        except Exception as exc:  # pragma: no cover - external dependency errors
            raise TranscriptionError("OpenAI transcription request failed") from exc

        response_obj = _to_plain_dict(response)
        text = str(response_obj.get("text") or "").strip()
        response_language = response_obj.get("language")
        normalized_language = (
            str(response_language) if isinstance(response_language, str) else language
        )

        raw_segments = response_obj.get("segments") or []
        parsed_segments: list[Segment] = []

        if isinstance(raw_segments, list):
            for raw_segment in raw_segments:
                segment = _to_plain_dict(raw_segment)
                segment_text = str(segment.get("text") or "").strip()
                if not segment_text:
                    continue

                start_raw = segment.get("start", 0.0)
                end_raw = segment.get("end", start_raw)
                try:
                    start = float(start_raw)
                    end = float(end_raw)
                except (TypeError, ValueError):
                    start = 0.0
                    end = 0.0

                parsed_segments.append(Segment(start=start, end=end, text=segment_text))

        if not parsed_segments and text:
            parsed_segments = [Segment(start=0.0, end=0.0, text=text)]

        if not text and parsed_segments:
            text = " ".join(segment.text for segment in parsed_segments).strip()

        if not text:
            raise TranscriptionError("Transcription returned empty text")

        return TranscriptResult(
            text=text,
            segments=parsed_segments,
            language=normalized_language,
            source=f"openai:{self.model}",
        )

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise TranscriptionError(
                "openai package is not installed. Install with `pip install openai`."
            ) from exc
        try:
            self.client = OpenAI()
        except Exception as exc:
            raise TranscriptionError(
                "Failed to initialize OpenAI client. Set OPENAI_API_KEY or choose local transcriber."
            ) from exc
        return self.client


class FasterWhisperTranscriber(Transcriber):
    """Local transcription via faster-whisper."""

    def __init__(
        self,
        model_size: str = "small",
        device: str = "auto",
        compute_type: str = "int8",
    ) -> None:
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model: Any | None = None

    def transcribe(
        self, audio_path: Path, language: str | None = None
    ) -> TranscriptResult:
        if not audio_path.exists():
            raise TranscriptionError(f"Audio file does not exist: {audio_path}")

        model = self._get_model()
        try:
            segments_iter, info = model.transcribe(
                str(audio_path),
                language=language,
                vad_filter=True,
            )
            parsed_segments: list[Segment] = []
            for segment in segments_iter:
                text = str(getattr(segment, "text", "")).strip()
                if not text:
                    continue
                start = float(getattr(segment, "start", 0.0))
                end = float(getattr(segment, "end", start))
                parsed_segments.append(Segment(start=start, end=end, text=text))
        except Exception as exc:  # pragma: no cover - external dependency errors
            raise TranscriptionError("faster-whisper transcription failed") from exc

        if not parsed_segments:
            raise TranscriptionError("Transcription returned empty text")

        full_text = " ".join(segment.text for segment in parsed_segments).strip()
        detected_language = getattr(info, "language", None)
        normalized_language = (
            str(detected_language) if isinstance(detected_language, str) else language
        )

        return TranscriptResult(
            text=full_text,
            segments=parsed_segments,
            language=normalized_language,
            source=f"faster-whisper:{self.model_size}",
        )

    def _get_model(self) -> Any:
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except ModuleNotFoundError as exc:
            raise TranscriptionError(
                "faster-whisper is not installed. Install with `pip install faster-whisper`."
            ) from exc
        try:
            self._model = WhisperModel(
                self.model_size, device=self.device, compute_type=self.compute_type
            )
        except Exception as exc:
            raise TranscriptionError(
                "Failed to initialize faster-whisper model."
            ) from exc
        return self._model


def _to_plain_dict(obj: Any) -> dict[str, Any]:
    if isinstance(obj, dict):
        return obj
    model_dump = getattr(obj, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        if isinstance(dumped, dict):
            return dumped
    return {}
