#!/usr/bin/env python3
"""
Verify speaker attribution against source transcript metadata and content.

Deterministic check: every person.name in predictions.json and risk-signals.json
MUST appear in the source transcript's metadata.guests array. Additionally checks
that the speaker name appears in the transcript intro (first 50 segments).

This prevents misattributions like the Hinton/Bengio bug where a clickbait video
title ("Godfather of AI") caused wrong speaker assignment.

Usage:
    python3 scripts/verify-speakers.py                 # Report only
    python3 scripts/verify-speakers.py --strict        # Fail on any mismatch
    python3 scripts/verify-speakers.py --video-id X    # Single video
    python3 scripts/verify-speakers.py --verbose       # Show all results
    python3 scripts/verify-speakers.py --dataset risk  # Only check risk-signals.json
    python3 scripts/verify-speakers.py --dataset pred  # Only check predictions.json
    python3 scripts/verify-speakers.py --dataset both  # Check both (default)
"""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = PROJECT_ROOT / "data" / "risk-signals.json"
PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions.json"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed.json"

# Known hosts/interviewers who should NEVER be attributed as speakers.
# If any signal/prediction has one of these as person.name, it's a flag.
KNOWN_HOSTS = {
    "lex fridman",
    "chris anderson",
    "ezra klein",
    "cleo abram",
    "harry stebbings",
    "dwarkesh patel",
    "lenny rachitsky",
    "zanny minton beddoes",
    "francine lacqua",
    "emma tucker",
    "roula khalaf",
    "nikhil kamath",
    "ross douthat",
    "andrew ross sorkin",
    "kara swisher",
    "scott pelley",
    "erik torenberg",
    "packy mccormick",
}

# Generic/anonymous attributions that should never appear
INVALID_NAMES = {
    "guest contributor",
    "panel speaker",
    "audience member",
    "unknown",
    "speaker",
    "host",
    "interviewer",
    "moderator",
}

INTRO_SEGMENT_COUNT = 50  # How many segments to scan for speaker introduction


def load_json(path):
    with open(path) as f:
        return json.load(f)


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


def load_transcript(transcript_path):
    """Load transcript and return (metadata, segments)."""
    data = load_json(transcript_path)
    metadata = data.get("metadata", {})
    segments = data.get("segments", [])
    return metadata, segments


def normalize_name(name):
    """Normalize a name for comparison: lowercase, strip whitespace."""
    return name.lower().strip()


def name_matches_guest(name, guest):
    """Check if a speaker name matches a guest entry.

    Handles common variations:
    - Exact match (case-insensitive)
    - First+last name match (handles middle names, titles)
    - Last name match when unambiguous
    """
    n = normalize_name(name)
    g = normalize_name(guest)

    # Exact match
    if n == g:
        return True

    # One contains the other (handles "Sam Altman" vs "Samuel Altman")
    if n in g or g in n:
        return True

    # Last name match (both must have at least 2 parts)
    n_parts = n.split()
    g_parts = g.split()
    if len(n_parts) >= 2 and len(g_parts) >= 2:
        # Compare last names
        if n_parts[-1] == g_parts[-1]:
            # Also check first name initial matches
            if n_parts[0][0] == g_parts[0][0]:
                return True

    return False


def name_in_guests(name, guests):
    """Check if a speaker name matches any guest in the list."""
    for guest in guests:
        if name_matches_guest(name, guest):
            return True
    return False


def name_in_intro(name, segments):
    """Check if a speaker name appears in the first N segments of the transcript."""
    n = normalize_name(name)
    name_parts = n.split()

    # Search intro segments for the name
    intro_text = " ".join(
        seg.get("text", "") for seg in segments[:INTRO_SEGMENT_COUNT]
    ).lower()

    # Try full name
    if n in intro_text:
        return True

    # Try last name only (if distinctive enough — at least 4 chars)
    if len(name_parts) >= 2 and len(name_parts[-1]) >= 4:
        if name_parts[-1] in intro_text:
            return True

    return False


def name_in_full_transcript(name, segments):
    """Check if a speaker name appears anywhere in the full transcript."""
    n = normalize_name(name)
    name_parts = n.split()
    last_name = name_parts[-1] if len(name_parts) >= 2 else n

    # Search all segments
    for seg in segments:
        text = seg.get("text", "").lower()
        if n in text:
            return True
        # Try last name (at least 4 chars to avoid false positives)
        if len(last_name) >= 4 and last_name in text:
            return True

    return False


def classify_speaker(name, video_id, metadata, segments):
    """Classify a speaker attribution.

    Returns (classification, details_string).
    Classifications:
        - verified: name in guests AND in intro
        - guest_only: name in guests but NOT in intro (weaker but acceptable)
        - intro_only: name in intro but NOT in guests (metadata gap)
        - transcript_only: name found in transcript body but not guests or intro
        - invalid_name: generic/anonymous attribution
        - known_host: attributed to a known interviewer/host
        - no_guests: transcript has empty guests array (data quality issue)
        - mismatch: name not found in guests, intro, or transcript
        - no_transcript: transcript file not found
    """
    if metadata is None:
        return "no_transcript", "Transcript file not found"

    n = normalize_name(name)

    # Check for invalid/generic names
    if n in INVALID_NAMES:
        return "invalid_name", f"'{name}' is a generic/anonymous attribution"

    # Check for known hosts
    if n in KNOWN_HOSTS:
        return "known_host", f"'{name}' is a known host/interviewer, not an AI principal"

    guests = metadata.get("guests", [])

    # Check for empty guests array
    if not guests:
        return "no_guests", f"Transcript has no metadata.guests — cannot verify speaker"

    in_guests = name_in_guests(name, guests)
    in_intro = name_in_intro(name, segments)
    in_transcript = name_in_full_transcript(name, segments) if not in_intro else True

    if in_guests and in_intro:
        return "verified", f"'{name}' matches guest {guests} and found in intro"

    if in_guests and not in_intro:
        if in_transcript:
            return "guest_only", (
                f"'{name}' matches guest {guests} but NOT found in first "
                f"{INTRO_SEGMENT_COUNT} segments (found later in transcript)"
            )
        return "guest_only", (
            f"'{name}' matches guest {guests} but name not found in transcript text"
        )

    if not in_guests and in_intro:
        return "intro_only", (
            f"'{name}' found in intro but NOT in metadata.guests {guests}"
        )

    if not in_guests and in_transcript:
        return "transcript_only", (
            f"'{name}' found in transcript body but NOT in metadata.guests {guests}"
        )

    return "mismatch", (
        f"'{name}' NOT found in metadata.guests {guests}, "
        f"NOT in intro, NOT in transcript"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verify speaker attribution against source transcripts"
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit with error if ANY speakers fail verification"
    )
    parser.add_argument("--video-id", help="Only verify for this video ID")
    parser.add_argument(
        "--verbose", action="store_true", help="Show all results including verified"
    )
    parser.add_argument(
        "--dataset", choices=["risk", "pred", "both"], default="both",
        help="Which dataset to verify (default: both)"
    )
    args = parser.parse_args()

    # Load common data
    processed_data = load_json(PROCESSED_PATH)
    transcript_map = build_transcript_map(processed_data)

    # Cache loaded transcripts
    transcript_cache = {}

    def get_transcript(video_id):
        if video_id not in transcript_cache:
            tpath = transcript_map.get(video_id)
            if tpath:
                transcript_cache[video_id] = load_transcript(tpath)
            else:
                transcript_cache[video_id] = (None, None)
        return transcript_cache[video_id]

    # Collect all items to verify
    items = []  # (dataset_name, item_id, person_name, video_id)

    if args.dataset in ("risk", "both"):
        if SIGNALS_PATH.exists():
            signals_data = load_json(SIGNALS_PATH)
            for signal in signals_data.get("signals", []):
                vid = signal["source"]["video_id"]
                if args.video_id and vid != args.video_id:
                    continue
                items.append((
                    "risk-signal",
                    signal["id"],
                    signal["person"]["name"],
                    vid,
                ))

    if args.dataset in ("pred", "both"):
        if PREDICTIONS_PATH.exists():
            preds_data = load_json(PREDICTIONS_PATH)
            for pred in preds_data.get("predictions", []):
                vid = pred["source"]["video_id"]
                if args.video_id and vid != args.video_id:
                    continue
                items.append((
                    "prediction",
                    pred["id"],
                    pred["person"]["name"],
                    vid,
                ))

    if not items:
        print("No items to verify.")
        return 0

    # Classify all items
    results = {
        "verified": [],
        "guest_only": [],
        "intro_only": [],
        "transcript_only": [],
        "invalid_name": [],
        "known_host": [],
        "no_guests": [],
        "mismatch": [],
        "no_transcript": [],
    }

    # Deduplicate by (name, video_id) for efficiency — classify once, report per item
    speaker_classifications = {}  # (name, video_id) -> (classification, details)

    for dataset_name, item_id, person_name, video_id in items:
        key = (person_name, video_id)
        if key not in speaker_classifications:
            metadata, segments = get_transcript(video_id)
            classification, details = classify_speaker(
                person_name, video_id, metadata, segments or []
            )
            speaker_classifications[key] = (classification, details)

        classification, details = speaker_classifications[key]
        results[classification].append((dataset_name, item_id, person_name, video_id, details))

    # Report
    total = sum(len(v) for v in results.values())
    passing = len(results["verified"]) + len(results["guest_only"])
    failing = total - passing

    print(f"\n{'='*70}")
    print(f"SPEAKER ATTRIBUTION VERIFICATION REPORT")
    print(f"{'='*70}")
    print(f"Total items checked: {total}")
    print()

    status_config = [
        ("verified", "Verified (in guests + in intro)", "\033[32m", False),
        ("guest_only", "Guest match only (in guests, not in intro)", "\033[32m", False),
        ("intro_only", "Intro only (in intro, NOT in guests)", "\033[33m", True),
        ("transcript_only", "Transcript only (in body, NOT in guests)", "\033[33m", True),
        ("invalid_name", "Invalid name (generic/anonymous)", "\033[31m", True),
        ("known_host", "Known host/interviewer", "\033[31m", True),
        ("no_guests", "No guest metadata in transcript", "\033[31m", True),
        ("mismatch", "Mismatch (not found anywhere)", "\033[31m", True),
        ("no_transcript", "No transcript file", "\033[90m", True),
    ]

    for category, label, color, is_failure in status_config:
        count = len(results[category])
        if count > 0 or args.verbose:
            pct = (count / total * 100) if total > 0 else 0
            print(f"  {color}{label}: {count} ({pct:.1f}%)\033[0m")

    print()

    # Show details for failures
    if args.verbose:
        for category, label, color, is_failure in status_config:
            if results[category]:
                print(f"\n--- {category.upper()} ---")
                for ds, item_id, name, vid, details in results[category]:
                    print(f"  [{ds}] {item_id}")
                    print(f"    Speaker: {name} | Video: {vid}")
                    print(f"    {details}")
    else:
        for category, label, color, is_failure in status_config:
            if is_failure and results[category]:
                print(f"\n--- {category.upper()} ---")
                # Group by (name, video_id) to avoid repetition
                seen = set()
                for ds, item_id, name, vid, details in results[category]:
                    key = (name, vid)
                    if key not in seen:
                        seen.add(key)
                        # Count how many items share this speaker+video
                        count = sum(
                            1 for d, i, n, v, _ in results[category]
                            if n == name and v == vid
                        )
                        print(f"  {name} in {vid} ({count} items)")
                        print(f"    {details}")
                        print()

    # Summary
    print(f"{'='*70}")
    if failing == 0:
        print(f"\033[32mPASS: All {total} items have verified speaker attribution\033[0m")
    else:
        print(f"\033[31mFAIL: {failing} items have unverified speaker attribution\033[0m")
        print()
        print("To fix:")
        if results["no_guests"]:
            print("  - Add metadata.guests to transcript JSON files (run transcribe.py with --guests)")
        if results["mismatch"]:
            print("  - Check speaker names against transcript — may be misattributed")
        if results["known_host"]:
            print("  - Remove signals/predictions attributed to hosts/interviewers")
        if results["invalid_name"]:
            print("  - Replace generic names with actual speaker names")
        if results["intro_only"] or results["transcript_only"]:
            print("  - Update metadata.guests in transcript JSON to include these speakers")

    # Strict mode
    if args.strict and failing > 0:
        print(f"\n\033[31mSTRICT MODE: {failing} items failed speaker verification\033[0m")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
