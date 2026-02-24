#!/bin/bash
# AI Pulse - Reprocess Predictions
# This script invokes Claude Code to batch-reprocess all existing transcripts
# for prediction extraction. Run this when the prediction schema changes or
# when you want to re-extract predictions from all interviews.
#
# Usage: ./scripts/reprocess-predictions.sh

set -euo pipefail

PROJECT_DIR="/Users/gian-lucasavino/Documents/Claude/ai-pulse"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "============================================"
echo "AI Pulse - Reprocess Predictions: $TIMESTAMP"
echo "============================================"

cd "$PROJECT_DIR"

export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.pyenv/shims:$PATH"

for cmd in python3 claude; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: $cmd not found in PATH"
        exit 1
    fi
done

claude --print \
    --max-turns 80 \
    --allowedTools "Bash(command:*),Read,Write,Edit,Glob,Grep" \
    "You are running as an automated reprocessing pipeline. Your task:

1. Read data/predictions.json and reset it to an empty skeleton (version 1, empty predictions array).
2. For each transcript JSON in data/transcripts/:
   a. Read the transcript (metadata + segments with timestamps).
   b. Extract all concrete, specific, falsifiable predictions. Look for:
      - Timeframe language ('by 2030', 'in 3 years', 'within a decade')
      - Prediction verbs ('will', 'expect', 'predict', 'my hunch is')
      - Confidence qualifiers ('90% probability', '50/50', 'almost certain')
      - AGI/ASI timelines, economic forecasts, tech milestones, job displacement, company predictions
      - Skip vague aspirational statements — only include specific, verifiable claims
   c. For each prediction, find the exact timestamp from the segments.
   d. Format each prediction as per the schema in CLAUDE.md Step 5b-ii.
   e. Add a '## Predictions' table section to the interview note (between Data Points and Topics).
   f. Add predictions_count to the note's frontmatter.
   g. Append predictions to data/predictions.json.
3. After all interviews are processed, update data/processed.json with predictions_count for each entry.
4. Regenerate vault/visualizations/predictions-timeline.html with the updated data.

Work autonomously. Follow CLAUDE.md instructions. Do not ask questions."

echo ""
echo "Reprocess predictions completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
