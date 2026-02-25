#!/usr/bin/env python3
"""
Verify risk signal quotes against source transcripts.

Cross-references every signal in data/risk-signals.json against its source
transcript to detect wrong timestamps, paraphrased quotes, and misattributed speakers.

Usage:
    python3 scripts/verify-risk-signals.py              # Report only
    python3 scripts/verify-risk-signals.py --fix        # Apply auto-fixes
    python3 scripts/verify-risk-signals.py --video-id X # Single video
    python3 scripts/verify-risk-signals.py --verbose    # Show all results
    python3 scripts/verify-risk-signals.py --strict     # Fail on paraphrased/ambiguous/bad speakers
"""

import argparse
import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = PROJECT_ROOT / "data" / "risk-signals.json"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed.json"

# Import speaker verification from verify-speakers.py (hyphenated filename)
_vs_spec = importlib.util.spec_from_file_location(
    "verify_speakers", PROJECT_ROOT / "scripts" / "verify-speakers.py"
)
_vs_mod = importlib.util.module_from_spec(_vs_spec)
_vs_spec.loader.exec_module(_vs_mod)
classify_speaker = _vs_mod.classify_speaker
load_transcript_with_meta = _vs_mod.load_transcript

TOLERANCE_SECONDS = 30  # ±30s counts as "verified"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def build_transcript_map(processed):
    """Map video_id -> transcript file path."""
    mapping = {}
    for v in processed.get("videos", []):
        vid = v.get("video_id")
        tpath = v.get("transcript_path")
        if vid and tpath:
            full = PROJECT_ROOT / tpath
            if full.exists():
                mapping[vid] = full
    return mapping


def load_segments(transcript_path):
    """Load transcript and return list of segments."""
    data = load_json(transcript_path)
    return data.get("segments", [])


def search_segments(segments, query, max_matches=10):
    """Search for query as case-insensitive substring in segments.
    Returns list of (segment_index, segment) tuples."""
    if not query:
        return []
    q = query.lower().strip()
    if not q:
        return []

    matches = []
    for i, seg in enumerate(segments):
        text = seg.get("text", "").lower()
        if q in text:
            matches.append((i, seg))
            if len(matches) >= max_matches:
                break
    return matches


def search_segment_windows(segments, query, window_size=2, max_matches=10):
    """Search across adjacent segment windows for phrases that span boundaries."""
    if not query:
        return []
    q = query.lower().strip()
    if not q:
        return []

    matches = []
    for i in range(len(segments) - window_size + 1):
        combined = " ".join(
            seg.get("text", "") for seg in segments[i : i + window_size]
        ).lower()
        if q in combined:
            matches.append((i, segments[i]))
            if len(matches) >= max_matches:
                break
    return matches


def format_timestamp(seconds):
    """Convert seconds to M:SS display format."""
    m = int(seconds) // 60
    s = int(seconds) % 60
    return f"{m}:{s:02d}"


def classify_signal(signal, segments):
    """Classify a signal's quote accuracy.

    Returns (classification, found_timestamp_or_none, details_string).
    Classifications: verified, fixable, ambiguous, paraphrased, null_quote, no_transcript
    """
    quote = signal.get("quote")
    claimed_ts = signal["source"].get("timestamp_seconds", 0)

    if segments is None:
        return "no_transcript", None, "Transcript file not found"

    if not quote:
        return "null_quote", None, "No quote text to verify"

    # Search for the quote in segments
    # Single-segment search
    matches = search_segments(segments, quote)

    # If not found, try multi-segment windows (2 through 8)
    for ws in range(2, 9):
        if not matches:
            matches = search_segment_windows(segments, quote, window_size=ws)

    if not matches:
        return "paraphrased", None, "No verbatim match found for quote"

    if len(matches) > 1:
        # Multiple matches — pick closest to claimed timestamp
        closest = min(matches, key=lambda m: abs(m[1]["start"] - claimed_ts))
        found_ts = closest[1]["start"]
        delta = abs(found_ts - claimed_ts)

        if delta <= TOLERANCE_SECONDS:
            return (
                "verified",
                found_ts,
                f"Matched quote at {format_timestamp(found_ts)} "
                f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s, "
                f"{len(matches)} matches, used closest)",
            )
        else:
            # Check if any match is within tolerance
            for _, seg in matches:
                if abs(seg["start"] - claimed_ts) <= TOLERANCE_SECONDS:
                    return (
                        "verified",
                        seg["start"],
                        f"Matched quote at {format_timestamp(seg['start'])} "
                        f"(claimed {format_timestamp(claimed_ts)}, "
                        f"{len(matches)} matches, one within tolerance)",
                    )
            # None within tolerance
            if len(matches) == 2:
                return (
                    "fixable",
                    found_ts,
                    f"Matched quote at {format_timestamp(found_ts)} "
                    f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s, "
                    f"2 matches, used closest)",
                )
            else:
                return (
                    "ambiguous",
                    found_ts,
                    f"Matched quote at {len(matches)} locations, "
                    f"none within ±{TOLERANCE_SECONDS}s of claimed "
                    f"{format_timestamp(claimed_ts)}",
                )

    # Single match
    found_ts = matches[0][1]["start"]
    delta = abs(found_ts - claimed_ts)

    if delta <= TOLERANCE_SECONDS:
        return (
            "verified",
            found_ts,
            f"Matched quote at {format_timestamp(found_ts)} "
            f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s)",
        )
    else:
        return (
            "fixable",
            found_ts,
            f"Matched quote at {format_timestamp(found_ts)} "
            f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s)",
        )


def fix_signal(signal, correct_ts, signals_data):
    """Update a signal's timestamp fields and ID. Returns old_id, new_id."""
    vid = signal["source"]["video_id"]
    old_id = signal["id"]
    old_ts = signal["source"]["timestamp_seconds"]
    new_ts = int(correct_ts)

    # Update source fields
    signal["source"]["timestamp_seconds"] = new_ts
    signal["source"]["timestamp_display"] = format_timestamp(new_ts)
    signal["source"]["timestamp_url"] = (
        f"https://www.youtube.com/watch?v={vid}&t={new_ts}s"
    )

    # Update ID
    new_id = f"risk-{vid}-{new_ts}"
    existing_ids = {s["id"] for s in signals_data["signals"]}
    if new_id in existing_ids and new_id != old_id:
        suffix = 1
        while f"{new_id}-{suffix}" in existing_ids:
            suffix += 1
        new_id = f"{new_id}-{suffix}"
    signal["id"] = new_id

    # Add verification metadata
    signal["verified"] = True
    signal["verified_date"] = date.today().isoformat()

    return old_id, new_id, old_ts, new_ts


def validate_signal(signal, transcript_path):
    """Validate a single signal against its transcript BEFORE saving.

    Returns (is_valid, corrected_signal_or_none, message).
    Used as a gate during extraction — reject signals that fail.
    """
    segments = load_segments(transcript_path)
    classification, found_ts, details = classify_signal(signal, segments)

    if classification == "verified":
        signal["verified"] = True
        signal["verified_date"] = date.today().isoformat()
        return True, signal, f"OK: {details}"

    if classification == "fixable" and found_ts is not None:
        vid = signal["source"]["video_id"]
        new_ts = int(found_ts)
        signal["source"]["timestamp_seconds"] = new_ts
        signal["source"]["timestamp_display"] = format_timestamp(new_ts)
        signal["source"]["timestamp_url"] = (
            f"https://www.youtube.com/watch?v={vid}&t={new_ts}s"
        )
        signal["id"] = f"risk-{vid}-{new_ts}"
        signal["verified"] = True
        signal["verified_date"] = date.today().isoformat()
        return True, signal, f"AUTO-FIXED: {details}"

    if classification == "null_quote":
        return True, signal, "OK: no quote text to verify"

    # Reject paraphrased, ambiguous, no_transcript
    return False, None, f"REJECTED ({classification}): {details}"


def main():
    parser = argparse.ArgumentParser(
        description="Verify risk signal quotes against source transcripts"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Apply auto-fixes for fixable mismatches"
    )
    parser.add_argument("--video-id", help="Only verify signals for this video ID")
    parser.add_argument(
        "--verbose", action="store_true", help="Show all results including verified"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with error if ANY signals are paraphrased or ambiguous"
    )
    args = parser.parse_args()

    # Load data
    signals_data = load_json(SIGNALS_PATH)
    processed_data = load_json(PROCESSED_PATH)
    transcript_map = build_transcript_map(processed_data)

    # Cache loaded segments per video
    segments_cache = {}

    def get_segments(video_id):
        if video_id not in segments_cache:
            tpath = transcript_map.get(video_id)
            if tpath:
                segments_cache[video_id] = load_segments(tpath)
            else:
                segments_cache[video_id] = None
        return segments_cache[video_id]

    # Classify all signals
    results = {
        "verified": [],
        "fixable": [],
        "ambiguous": [],
        "paraphrased": [],
        "null_quote": [],
        "no_transcript": [],
    }

    for signal in signals_data["signals"]:
        vid = signal["source"]["video_id"]
        if args.video_id and vid != args.video_id:
            continue

        segments = get_segments(vid)
        classification, found_ts, details = classify_signal(signal, segments)
        results[classification].append((signal, found_ts, details))

    # Report
    total = sum(len(v) for v in results.values())
    print(f"\n{'='*70}")
    print(f"RISK SIGNAL QUOTE VERIFICATION REPORT")
    print(f"{'='*70}")
    print(f"Total signals checked: {total}")
    print()

    for category, label, color in [
        ("verified", "Verified (within ±30s)", "\033[32m"),
        ("fixable", "Fixable (found but off by >30s)", "\033[33m"),
        ("ambiguous", "Ambiguous (multiple matches, unclear)", "\033[35m"),
        ("paraphrased", "Paraphrased (quote not found verbatim)", "\033[31m"),
        ("null_quote", "Null quote (no text to verify)", "\033[36m"),
        ("no_transcript", "No transcript file", "\033[90m"),
    ]:
        count = len(results[category])
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {color}{label}: {count} ({pct:.1f}%)\033[0m")

    print()

    # Show details for non-verified
    if args.verbose:
        for category in ["verified", "fixable", "ambiguous", "paraphrased", "null_quote", "no_transcript"]:
            if results[category]:
                print(f"\n--- {category.upper()} ---")
                for signal, found_ts, details in results[category]:
                    print(f"  [{signal['id']}] {signal.get('quote', 'N/A')[:60]}...")
                    print(f"    {details}")
    else:
        for category in ["fixable", "ambiguous", "paraphrased"]:
            if results[category]:
                print(f"\n--- {category.upper()} ---")
                for signal, found_ts, details in results[category]:
                    print(f"  [{signal['id']}]")
                    print(f"    Quote: {signal.get('quote', 'N/A')[:80]}")
                    print(f"    {details}")
                    print()

    # Apply fixes
    if args.fix and results["fixable"]:
        print(f"\n{'='*70}")
        print(f"APPLYING FIXES ({len(results['fixable'])} signals)")
        print(f"{'='*70}")

        fixed_count = 0

        for signal, found_ts, details in results["fixable"]:
            old_id, new_id, old_ts, new_ts = fix_signal(
                signal, found_ts, signals_data
            )
            fixed_count += 1
            print(f"  Fixed: {old_id} -> {new_id}")
            print(f"    Timestamp: {format_timestamp(old_ts)} -> {format_timestamp(new_ts)}")

        # Also mark verified signals
        for signal, found_ts, details in results["verified"]:
            if not signal.get("verified"):
                signal["verified"] = True
                signal["verified_date"] = date.today().isoformat()

        # Update totals
        signals_data["total_signals"] = len(signals_data["signals"])
        signals_data["last_updated"] = date.today().isoformat()

        # Save updated signals
        save_json(SIGNALS_PATH, signals_data)
        print(f"\nSaved {fixed_count} fixes to {SIGNALS_PATH.relative_to(PROJECT_ROOT)}")

    elif args.fix and not results["fixable"]:
        print("\nNo fixable mismatches found — nothing to fix.")

    # Summary of remaining issues
    remaining = len(results["paraphrased"]) + len(results["ambiguous"])
    if remaining > 0:
        print(f"\n⚠ {remaining} signals need manual review:")
        print(f"  - {len(results['paraphrased'])} have paraphrased quotes (need re-extraction from transcript)")
        print(f"  - {len(results['ambiguous'])} have ambiguous matches (multiple locations)")

    # Speaker verification (always runs in --strict mode)
    speaker_failures = 0
    if args.strict:
        print(f"\n{'='*70}")
        print(f"SPEAKER ATTRIBUTION CHECK")
        print(f"{'='*70}")

        # Cache transcript metadata per video
        transcript_meta_cache = {}

        def get_transcript_meta(video_id):
            if video_id not in transcript_meta_cache:
                tpath = transcript_map.get(video_id)
                if tpath:
                    transcript_meta_cache[video_id] = load_transcript_with_meta(tpath)
                else:
                    transcript_meta_cache[video_id] = (None, None)
            return transcript_meta_cache[video_id]

        speaker_results = {}  # (name, vid) -> (classification, details)
        for signal in signals_data["signals"]:
            vid = signal["source"]["video_id"]
            if args.video_id and vid != args.video_id:
                continue
            name = signal["person"]["name"]
            key = (name, vid)
            if key not in speaker_results:
                metadata, segs = get_transcript_meta(vid)
                classification, details = classify_speaker(name, vid, metadata, segs or [])
                speaker_results[key] = (classification, details)

        # Count pass/fail
        passing_classes = {"verified", "guest_only"}
        for (name, vid), (classification, details) in sorted(speaker_results.items()):
            if classification not in passing_classes:
                speaker_failures += 1
                print(f"  \033[31mFAIL: {name} in {vid} — {classification}: {details}\033[0m")
            elif args.verbose:
                print(f"  \033[32mOK: {name} in {vid} — {classification}\033[0m")

        if speaker_failures == 0:
            print(f"  \033[32mAll speakers verified against transcript metadata\033[0m")
        else:
            print(f"\n  \033[31m{speaker_failures} speaker attribution failures\033[0m")

    # Strict mode: fail if any signals are paraphrased, ambiguous, or misattributed
    total_failures = remaining + speaker_failures
    if args.strict and total_failures > 0:
        print(f"\n✗ STRICT MODE: {total_failures} signals failed verification")
        return 1

    return 0 if not results["fixable"] or args.fix else 1


if __name__ == "__main__":
    sys.exit(main())
