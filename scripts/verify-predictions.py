#!/usr/bin/env python3
"""
Verify prediction timestamps against source transcripts.

Cross-references every prediction in data/predictions.json against its source
transcript to detect wrong timestamps, paraphrased raw text, and misattributed speakers.

Usage:
    python3 scripts/verify-predictions.py              # Report only
    python3 scripts/verify-predictions.py --fix        # Apply auto-fixes
    python3 scripts/verify-predictions.py --video-id X # Single video
    python3 scripts/verify-predictions.py --verbose    # Show all results
    python3 scripts/verify-predictions.py --strict     # Fail on paraphrased/ambiguous/bad speakers
"""

import argparse
import importlib.util
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions.json"
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


def classify_prediction(pred, segments):
    """Classify a prediction's timestamp accuracy.

    Returns (classification, found_timestamp_or_none, details_string).
    Classifications: verified, fixable, ambiguous, paraphrased, null_raw, no_transcript
    """
    timeframe_raw = (pred.get("timeframe") or {}).get("raw")
    confidence_raw = (pred.get("confidence") or {}).get("raw")
    claimed_ts = pred["source"].get("timestamp_seconds", 0)

    if segments is None:
        return "no_transcript", None, "Transcript file not found"

    # Try timeframe.raw first, then confidence.raw as fallback
    search_texts = []
    if timeframe_raw:
        search_texts.append(("timeframe.raw", timeframe_raw))
    if confidence_raw:
        search_texts.append(("confidence.raw", confidence_raw))

    if not search_texts:
        return "null_raw", None, "No raw text fields to verify"

    for field_name, raw_text in search_texts:
        # Single-segment search
        matches = search_segments(segments, raw_text)

        # If not found, try 2-segment windows
        if not matches:
            matches = search_segment_windows(segments, raw_text, window_size=2)

        # If not found, try 3-segment windows
        if not matches:
            matches = search_segment_windows(segments, raw_text, window_size=3)

        # For micro-segmented transcripts (e.g. WEF), try wider windows
        for ws in (4, 5, 6, 8):
            if not matches:
                matches = search_segment_windows(segments, raw_text, window_size=ws)

        if not matches:
            continue

        if len(matches) > 1:
            # Multiple matches — pick closest to claimed timestamp
            closest = min(matches, key=lambda m: abs(m[1]["start"] - claimed_ts))
            found_ts = closest[1]["start"]
            delta = abs(found_ts - claimed_ts)

            if delta <= TOLERANCE_SECONDS:
                return (
                    "verified",
                    found_ts,
                    f"Matched {field_name} at {format_timestamp(found_ts)} "
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
                            f"Matched {field_name} at {format_timestamp(seg['start'])} "
                            f"(claimed {format_timestamp(claimed_ts)}, "
                            f"{len(matches)} matches, one within tolerance)",
                        )
                # None within tolerance — ambiguous if many, fixable if clearly one best
                if len(matches) == 2:
                    return (
                        "fixable",
                        found_ts,
                        f"Matched {field_name} at {format_timestamp(found_ts)} "
                        f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s, "
                        f"2 matches, used closest)",
                    )
                else:
                    return (
                        "ambiguous",
                        found_ts,
                        f"Matched {field_name} at {len(matches)} locations, "
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
                f"Matched {field_name} at {format_timestamp(found_ts)} "
                f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s)",
            )
        else:
            return (
                "fixable",
                found_ts,
                f"Matched {field_name} at {format_timestamp(found_ts)} "
                f"(claimed {format_timestamp(claimed_ts)}, Δ{delta:.0f}s)",
            )

    # None of the raw texts were found
    tried = ", ".join(f for f, _ in search_texts)
    return "paraphrased", None, f"No verbatim match found (searched: {tried})"


def fix_prediction(pred, correct_ts, predictions_data):
    """Update a prediction's timestamp fields and ID. Returns old_id, new_id."""
    vid = pred["source"]["video_id"]
    old_id = pred["id"]
    old_ts = pred["source"]["timestamp_seconds"]
    new_ts = int(correct_ts)

    # Update source fields
    pred["source"]["timestamp_seconds"] = new_ts
    pred["source"]["timestamp_display"] = format_timestamp(new_ts)
    pred["source"]["timestamp_url"] = (
        f"https://www.youtube.com/watch?v={vid}&t={new_ts}s"
    )

    # Update ID
    new_id = f"pred-{vid}-{new_ts}"
    # Check for ID collision
    existing_ids = {p["id"] for p in predictions_data["predictions"]}
    if new_id in existing_ids and new_id != old_id:
        # Append a suffix to avoid collision
        suffix = 1
        while f"{new_id}-{suffix}" in existing_ids:
            suffix += 1
        new_id = f"{new_id}-{suffix}"
    pred["id"] = new_id

    # Add verification metadata
    pred["verified"] = True
    pred["verified_date"] = date.today().isoformat()

    return old_id, new_id, old_ts, new_ts


def update_vault_note(note_path, old_ts, new_ts, video_id):
    """Replace old timestamp URLs with new ones in the vault markdown note."""
    full_path = PROJECT_ROOT / note_path
    if not full_path.exists():
        return False

    content = full_path.read_text()
    old_url_part = f"&t={old_ts}s"
    new_url_part = f"&t={new_ts}s"
    old_display = format_timestamp(old_ts)
    new_display = format_timestamp(new_ts)

    # Replace timestamp URLs for this video
    old_pattern = f"watch?v={video_id}&t={old_ts}s"
    new_pattern = f"watch?v={video_id}&t={new_ts}s"

    if old_pattern not in content:
        return False

    updated = content.replace(old_pattern, new_pattern)
    # Also update display timestamps in the same links
    # Pattern: [▶ M:SS](url) — replace display only when adjacent to the URL we just fixed
    updated = updated.replace(
        f"[▶ {old_display}]({new_pattern.replace('watch?v=', 'https://www.youtube.com/watch?v=')})",
        f"[▶ {new_display}]({new_pattern.replace('watch?v=', 'https://www.youtube.com/watch?v=')})",
    )

    full_path.write_text(updated)
    return True


def validate_prediction(pred, transcript_path):
    """Validate a single prediction against its transcript BEFORE saving.

    Returns (is_valid, corrected_pred_or_none, message).
    Used as a gate during extraction — reject predictions that fail.
    """
    segments = load_segments(transcript_path)
    classification, found_ts, details = classify_prediction(pred, segments)

    if classification == "verified":
        pred["verified"] = True
        pred["verified_date"] = date.today().isoformat()
        return True, pred, f"OK: {details}"

    if classification == "fixable" and found_ts is not None:
        vid = pred["source"]["video_id"]
        new_ts = int(found_ts)
        pred["source"]["timestamp_seconds"] = new_ts
        pred["source"]["timestamp_display"] = format_timestamp(new_ts)
        pred["source"]["timestamp_url"] = (
            f"https://www.youtube.com/watch?v={vid}&t={new_ts}s"
        )
        pred["id"] = f"pred-{vid}-{new_ts}"
        pred["verified"] = True
        pred["verified_date"] = date.today().isoformat()
        return True, pred, f"AUTO-FIXED: {details}"

    if classification == "null_raw":
        return True, pred, "OK: no raw text to verify (null timeframe)"

    # Reject paraphrased, ambiguous, no_transcript
    return False, None, f"REJECTED ({classification}): {details}"


def main():
    parser = argparse.ArgumentParser(
        description="Verify prediction timestamps against source transcripts"
    )
    parser.add_argument(
        "--fix", action="store_true", help="Apply auto-fixes for fixable mismatches"
    )
    parser.add_argument("--video-id", help="Only verify predictions for this video ID")
    parser.add_argument(
        "--verbose", action="store_true", help="Show all results including verified"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with error if ANY predictions are paraphrased or ambiguous"
    )
    args = parser.parse_args()

    # Load data
    predictions_data = load_json(PREDICTIONS_PATH)
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

    # Classify all predictions
    results = {
        "verified": [],
        "fixable": [],
        "ambiguous": [],
        "paraphrased": [],
        "null_raw": [],
        "no_transcript": [],
    }

    for pred in predictions_data["predictions"]:
        vid = pred["source"]["video_id"]
        if args.video_id and vid != args.video_id:
            continue

        segments = get_segments(vid)
        classification, found_ts, details = classify_prediction(pred, segments)
        results[classification].append((pred, found_ts, details))

    # Report
    total = sum(len(v) for v in results.values())
    print(f"\n{'='*70}")
    print(f"PREDICTION TIMESTAMP VERIFICATION REPORT")
    print(f"{'='*70}")
    print(f"Total predictions checked: {total}")
    print()

    for category, label, color in [
        ("verified", "Verified (within ±30s)", "\033[32m"),
        ("fixable", "Fixable (found but off by >30s)", "\033[33m"),
        ("ambiguous", "Ambiguous (multiple matches, unclear)", "\033[35m"),
        ("paraphrased", "Paraphrased (raw text not found verbatim)", "\033[31m"),
        ("null_raw", "Null raw (no text to verify)", "\033[36m"),
        ("no_transcript", "No transcript file", "\033[90m"),
    ]:
        count = len(results[category])
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {color}{label}: {count} ({pct:.1f}%)\033[0m")

    print()

    # Show details for non-verified
    if args.verbose:
        for category in ["verified", "fixable", "ambiguous", "paraphrased", "null_raw", "no_transcript"]:
            if results[category]:
                print(f"\n--- {category.upper()} ---")
                for pred, found_ts, details in results[category]:
                    print(f"  [{pred['id']}] {pred['prediction'][:60]}...")
                    print(f"    {details}")
    else:
        for category in ["fixable", "ambiguous", "paraphrased"]:
            if results[category]:
                print(f"\n--- {category.upper()} ---")
                for pred, found_ts, details in results[category]:
                    print(f"  [{pred['id']}]")
                    print(f"    Prediction: {pred['prediction'][:80]}")
                    raw = (pred.get("timeframe") or {}).get("raw", "N/A")
                    print(f"    timeframe.raw: {raw}")
                    print(f"    {details}")
                    print()

    # Apply fixes
    if args.fix and results["fixable"]:
        print(f"\n{'='*70}")
        print(f"APPLYING FIXES ({len(results['fixable'])} predictions)")
        print(f"{'='*70}")

        fixed_count = 0
        note_updates = 0

        for pred, found_ts, details in results["fixable"]:
            old_id, new_id, old_ts, new_ts = fix_prediction(
                pred, found_ts, predictions_data
            )
            fixed_count += 1
            print(f"  Fixed: {old_id} -> {new_id}")
            print(f"    Timestamp: {format_timestamp(old_ts)} -> {format_timestamp(new_ts)}")

            # Update vault note
            note_path = pred.get("note_path")
            if note_path and update_vault_note(note_path, old_ts, new_ts, pred["source"]["video_id"]):
                note_updates += 1
                print(f"    Updated vault note: {note_path}")

        # Also mark verified predictions
        for pred, found_ts, details in results["verified"]:
            if not pred.get("verified"):
                pred["verified"] = True
                pred["verified_date"] = date.today().isoformat()

        # Save updated predictions
        save_json(PREDICTIONS_PATH, predictions_data)
        print(f"\nSaved {fixed_count} fixes to {PREDICTIONS_PATH.relative_to(PROJECT_ROOT)}")
        print(f"Updated {note_updates} vault notes")
        print(
            f"\nReminder: regenerate vault/visualizations/predictions-timeline.html "
            f"with the updated predictions data."
        )

    elif args.fix and not results["fixable"]:
        print("\nNo fixable mismatches found — nothing to fix.")

    # Summary of remaining issues
    remaining = len(results["paraphrased"]) + len(results["ambiguous"])
    if remaining > 0:
        print(f"\n⚠ {remaining} predictions need manual review:")
        print(f"  - {len(results['paraphrased'])} have paraphrased raw text (need re-extraction from transcript)")
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
        for pred in predictions_data["predictions"]:
            vid = pred["source"]["video_id"]
            if args.video_id and vid != args.video_id:
                continue
            name = pred["person"]["name"]
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

    # Strict mode: fail if any predictions are paraphrased, ambiguous, or misattributed
    total_failures = remaining + speaker_failures
    if args.strict and total_failures > 0:
        print(f"\n✗ STRICT MODE: {total_failures} predictions failed verification")
        return 1

    return 0 if not results["fixable"] or args.fix else 1


if __name__ == "__main__":
    sys.exit(main())
