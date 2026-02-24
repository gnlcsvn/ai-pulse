#!/bin/bash
# AI Pulse - Cron entry point
# This script is called by cron and invokes Claude Code to run the pipeline.
#
# Cron setup (runs daily at 8am):
#   0 8 * * * /Users/gian-lucasavino/Documents/Claude/ai-pulse/scripts/run.sh >> /Users/gian-lucasavino/Documents/Claude/ai-pulse/data/cron.log 2>&1

set -euo pipefail

PROJECT_DIR="/Users/gian-lucasavino/Documents/Claude/ai-pulse"
LOG_FILE="$PROJECT_DIR/data/cron.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "============================================"
echo "AI Pulse Run: $TIMESTAMP"
echo "============================================"

# Ensure we're in the project directory
cd "$PROJECT_DIR"

# Set PATH to include common tool locations
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.pyenv/shims:$PATH"

# Check that required tools exist
for cmd in yt-dlp ffmpeg python3 claude; do
    if ! command -v "$cmd" &> /dev/null; then
        echo "ERROR: $cmd not found in PATH"
        exit 1
    fi
done

# Run Claude Code with the project's CLAUDE.md instructions
# --print mode for non-interactive execution
# --max-turns limits how many back-and-forth steps the agent can take
claude --print \
    --max-turns 50 \
    --allowedTools "Bash(command:*),Read,Write,Edit,Glob,Grep" \
    "You are running as an automated pipeline. Follow the CLAUDE.md instructions exactly. Execute the full pipeline: discover videos, filter, download, transcribe, extract facts, generate markdown notes and HTML visualizations. Process up to 3 new videos. Work autonomously - do not ask questions, make reasonable decisions. Start now."

echo ""
echo "AI Pulse run completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
