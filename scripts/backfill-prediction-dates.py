#!/usr/bin/env python3
"""
Backfill prediction_date on all predictions in data/predictions.json.

Sets prediction_date = upload_date for all predictions that don't already
have the field. This is the reasonable default — override manually when
the recording date is known to differ from the upload date.

Usage:
    python3 scripts/backfill-prediction-dates.py          # Dry run
    python3 scripts/backfill-prediction-dates.py --apply   # Write changes
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREDICTIONS_PATH = PROJECT_ROOT / "data" / "predictions.json"


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def main():
    parser = argparse.ArgumentParser(
        description="Backfill prediction_date on all predictions"
    )
    parser.add_argument(
        "--apply", action="store_true", help="Write changes to predictions.json"
    )
    args = parser.parse_args()

    data = load_json(PREDICTIONS_PATH)
    predictions = data["predictions"]

    already_set = 0
    backfilled = 0
    today = date.today().isoformat()

    # --- Audit: check predictions from 2025 videos ---
    current_date = datetime.strptime("2026-02-25", "%Y-%m-%d")
    expiring = []

    for pred in predictions:
        source = pred["source"]

        # Backfill prediction_date
        if "prediction_date" in source and source["prediction_date"]:
            already_set += 1
        else:
            source["prediction_date"] = source["upload_date"]
            backfilled += 1

        # Check for predictions with timeframe windows that may have passed
        upload = source["upload_date"]
        tf = pred.get("timeframe", {})
        earliest = tf.get("earliest_year")
        latest = tf.get("latest_year")

        if earliest and latest and upload < "2026-01-01":
            expiring.append({
                "id": pred["id"],
                "prediction": pred["prediction"],
                "person": pred["person"]["name"],
                "upload_date": upload,
                "prediction_date": source.get("prediction_date", upload),
                "timeframe_raw": tf.get("raw"),
                "earliest_year": earliest,
                "latest_year": latest,
                "status": "PASSED" if latest < 2026 else (
                    "WINDOW OPEN" if earliest <= 2026 else "FUTURE"
                ),
            })

    print(f"Total predictions: {len(predictions)}")
    print(f"Already had prediction_date: {already_set}")
    print(f"Backfilled (prediction_date = upload_date): {backfilled}")

    # Print audit of 2025-video predictions with dates
    if expiring:
        print(f"\n{'='*70}")
        print("AUDIT: Predictions from 2025 videos with date ranges")
        print(f"{'='*70}")
        for e in expiring:
            print(f"\n  [{e['id']}]")
            print(f"    {e['prediction'][:80]}")
            print(f"    By: {e['person']}")
            print(f"    Upload date: {e['upload_date']}")
            print(f"    Timeframe: {e['timeframe_raw']}")
            print(f"    Range: {e['earliest_year']}-{e['latest_year']}")
            print(f"    Status: {e['status']}")

    # Also show all 2025-video predictions (including undated)
    preds_2025 = [p for p in predictions if p["source"]["upload_date"] < "2026-01-01"]
    print(f"\n{'='*70}")
    print(f"ALL predictions from 2025 videos: {len(preds_2025)}")
    print(f"{'='*70}")
    for p in preds_2025:
        tf = p.get("timeframe", {})
        years = f"{tf.get('earliest_year', '?')}-{tf.get('latest_year', '?')}"
        print(f"  [{p['id']}] {p['prediction'][:70]}")
        print(f"    Upload: {p['source']['upload_date']} | Timeframe: {tf.get('raw', 'null')} | Years: {years}")

    if args.apply:
        data["last_updated"] = today
        save_json(PREDICTIONS_PATH, data)
        print(f"\nSaved {backfilled} updates to {PREDICTIONS_PATH.relative_to(PROJECT_ROOT)}")
    else:
        print(f"\nDry run — use --apply to write changes")

    return 0


if __name__ == "__main__":
    sys.exit(main())
