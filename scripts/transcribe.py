#!/usr/bin/env python3
"""Transcribe audio files using mlx-whisper (Apple Silicon optimized).

Outputs both JSON (with per-segment timestamps and metadata) and TXT formats.
The JSON includes full video metadata so transcripts are self-contained
and reusable without needing to look up external sources.

Usage:
  python3 scripts/transcribe.py data/audio/VIDEO_ID.mp3 \\
    --video-id VIDEO_ID \\
    --title "Interview Title" \\
    --channel "Channel Name" \\
    --upload-date 2026-02-19 \\
    --url "https://www.youtube.com/watch?v=VIDEO_ID" \\
    --slug "2026-02-19_interview-title-slug"

  # Minimal (without metadata - not recommended):
  python3 scripts/transcribe.py data/audio/VIDEO_ID.mp3
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


def slugify(text: str, max_len: int = 60) -> str:
    """Convert text to a URL-friendly slug."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text.strip())
    text = re.sub(r"-+", "-", text)
    return text[:max_len].rstrip("-")


def transcribe(audio_path: str, model: str, language: str | None) -> dict:
    """Transcribe using local mlx-whisper."""
    import mlx_whisper

    kwargs = {"path_or_hf_repo": model, "verbose": True}
    if language:
        kwargs["language"] = language

    print(f"Transcribing with mlx-whisper (model: {model})...")
    result = mlx_whisper.transcribe(audio_path, **kwargs)

    segments = []
    for seg in result.get("segments", []):
        segments.append({
            "id": seg.get("id", len(segments)),
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip(),
        })

    return {
        "text": result["text"].strip(),
        "language": result.get("language", language or "unknown"),
        "segments": segments,
    }


def main():
    parser = argparse.ArgumentParser(description="Transcribe audio with mlx-whisper.")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("-l", "--language", default=None,
                        help="Language code (e.g. en, de). Auto-detected if omitted.")
    parser.add_argument("-o", "--output-dir", default="data/transcripts",
                        help="Output directory (default: data/transcripts)")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo",
                        help="MLX whisper model (default: mlx-community/whisper-large-v3-turbo)")

    # Metadata arguments
    parser.add_argument("--video-id", default=None, help="YouTube video ID")
    parser.add_argument("--title", default=None, help="Video title")
    parser.add_argument("--channel", default=None, help="YouTube channel name")
    parser.add_argument("--upload-date", default=None, help="Upload date (YYYY-MM-DD)")
    parser.add_argument("--url", default=None, help="Full YouTube URL")
    parser.add_argument("--duration", default=None, help="Video duration (e.g. 87m, 1h23m)")
    parser.add_argument("--guests", default=None, help="Comma-separated guest names")
    parser.add_argument("--slug", default=None,
                        help="Output filename slug (e.g. 2026-02-19_boris-cherny-head-of-claude-code). "
                             "If omitted, uses upload-date + slugified title, or falls back to video ID.")

    args = parser.parse_args()

    audio_path = Path(args.audio).resolve()
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Determine output filename
    if args.slug:
        stem = args.slug
    elif args.upload_date and args.title:
        stem = f"{args.upload_date}_{slugify(args.title)}"
    else:
        stem = audio_path.stem

    # Build metadata
    video_id = args.video_id or audio_path.stem
    metadata = {
        "video_id": video_id,
        "url": args.url or f"https://www.youtube.com/watch?v={video_id}",
        "title": args.title,
        "channel": args.channel,
        "upload_date": args.upload_date,
        "duration": args.duration,
        "guests": [g.strip() for g in args.guests.split(",")] if args.guests else None,
        "transcribed_date": datetime.now().strftime("%Y-%m-%d"),
        "whisper_model": args.model,
    }
    # Remove None values
    metadata = {k: v for k, v in metadata.items() if v is not None}

    try:
        result = transcribe(str(audio_path), args.model, args.language)
    except ImportError as e:
        print(f"Error: mlx-whisper not installed. Run: pip3 install mlx-whisper", file=sys.stderr)
        print(f"Details: {e}", file=sys.stderr)
        sys.exit(1)

    # Build final JSON with metadata at the top level
    output = {
        "metadata": metadata,
        "language": result["language"],
        "text": result["text"],
        "segments": result["segments"],
    }

    # Write JSON with segments and metadata
    json_path = output_dir / f"{stem}.json"
    json_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"JSON transcript: {json_path}")

    # Write plain text
    txt_path = output_dir / f"{stem}.txt"
    txt_path.write_text(result["text"], encoding="utf-8")
    print(f"TXT transcript:  {txt_path}")


if __name__ == "__main__":
    main()
