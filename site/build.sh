#!/bin/bash
# Sync pipeline data into the site's public directory.
# Run this before `npm run build` or during dev to refresh data.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DATA_DIR="$SCRIPT_DIR/public/data"

mkdir -p "$DATA_DIR"

# Extract predictions array
python3 -c "
import json, sys
with open('$PROJECT_ROOT/data/predictions.json') as f:
    data = json.load(f)
preds = data['predictions'] if isinstance(data, dict) and 'predictions' in data else data
json.dump(preds, sys.stdout)
" > "$DATA_DIR/predictions.json"

echo "Synced $(python3 -c "import json; print(len(json.load(open('$DATA_DIR/predictions.json'))))")" predictions

# Extract risk signals array (if exists)
if [ -f "$PROJECT_ROOT/data/risk-signals.json" ]; then
    python3 -c "
import json, sys
with open('$PROJECT_ROOT/data/risk-signals.json') as f:
    data = json.load(f)
signals = data['signals'] if isinstance(data, dict) and 'signals' in data else data
json.dump(signals, sys.stdout)
" > "$DATA_DIR/risk-signals.json"
    echo "Synced $(python3 -c "import json; print(len(json.load(open('$DATA_DIR/risk-signals.json'))))")" risk signals
fi
