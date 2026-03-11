"""CLI entrypoint for YouTube transcript generation."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate raw transcript data from a YouTube URL."
    )
    parser.add_argument("url", help="YouTube URL")
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download audio even if cache exists.",
    )
    parser.add_argument(
        "--force-transcribe",
        action="store_true",
        help="Re-transcribe even if transcript cache exists.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data"),
        help="Root output directory (default: data).",
    )
    parser.add_argument(
        "--prefer-captions",
        action="store_true",
        help="Reserved option for future caption-first transcript flow.",
    )
    parser.add_argument(
        "--transcriber",
        default="faster-whisper",
        choices=["faster-whisper", "openai"],
        help="Transcription backend (default: faster-whisper).",
    )
    parser.add_argument(
        "--openai-model",
        default="whisper-1",
        help="OpenAI transcription model (default: whisper-1).",
    )
    parser.add_argument(
        "--whisper-model",
        default="small",
        help="Local faster-whisper model size (default: small).",
    )
    parser.add_argument(
        "--whisper-device",
        default="auto",
        help="Local faster-whisper device (default: auto).",
    )
    parser.add_argument(
        "--whisper-compute-type",
        default="int8",
        help="Local faster-whisper compute type (default: int8).",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level (default: INFO).",
    )
    return parser


def configure_logging(log_level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    logger = logging.getLogger("youtube-transcript-cli")

    try:
        from youtube_transcript_cli.audio_cache_manager import AudioCacheManager
        from youtube_transcript_cli.exceptions import TranscriptCliError
        from youtube_transcript_cli.service import TranscriptService
        from youtube_transcript_cli.transcriber import (
            FasterWhisperTranscriber,
            OpenAITranscriber,
        )
        from youtube_transcript_cli.transcript_store import TranscriptStore
        from youtube_transcript_cli.youtube_resolver import YouTubeResolver
    except ModuleNotFoundError as exc:
        logger.error(
            "Missing dependency: %s. Run `pip install -r requirements.txt`.",
            exc.name,
        )
        return 1

    resolver = YouTubeResolver()
    audio_cache = AudioCacheManager(output_root=args.output_root, logger=logger)
    transcript_store = TranscriptStore(output_root=args.output_root)
    if args.transcriber == "openai":
        transcriber_factory = lambda: OpenAITranscriber(model=args.openai_model)
    else:
        transcriber_factory = lambda: FasterWhisperTranscriber(
            model_size=args.whisper_model,
            device=args.whisper_device,
            compute_type=args.whisper_compute_type,
        )

    service = TranscriptService(
        resolver=resolver,
        audio_cache=audio_cache,
        transcript_store=transcript_store,
        transcriber_factory=transcriber_factory,
        logger=logger,
    )

    try:
        result = service.run(
            url=args.url,
            force_download=args.force_download,
            force_transcribe=args.force_transcribe,
            prefer_captions=args.prefer_captions,
        )
    except TranscriptCliError as exc:
        logger.error("%s", exc)
        return 1
    except Exception:
        logger.exception("Unexpected error occurred.")
        return 1

    print(f"video_id={result['video_id']}")
    print(f"audio_path={result['audio_path']}")
    print(f"transcript_path={result['transcript_path']}")
    print(f"segments_path={result['segments_path']}")
    print(f"metadata_path={result['metadata_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
