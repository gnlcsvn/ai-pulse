#!/bin/bash
# AI Pulse - Extract Risk Signals
# This script invokes Claude Code to batch-process all existing transcripts
# for existential risk signal extraction. Creates data/risk-signals.json and
# generates the dead-or-alive.html visualization.
#
# Usage: ./scripts/extract-risk-signals.sh

set -euo pipefail

PROJECT_DIR="/Users/gian-lucasavino/Documents/Claude/ai-pulse"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "============================================"
echo "AI Pulse - Extract Risk Signals: $TIMESTAMP"
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
    "You are running as an automated risk signal extraction pipeline. Your task:

1. Read data/risk-signals.json and reset it to an empty skeleton (version 1, empty signals array).
2. For each transcript JSON in data/transcripts/:
   a. Read the transcript (metadata + segments with timestamps).
   b. FIRST: Read metadata.guests to identify who the speakers are. Only attribute quotes to people in this list. If metadata.guests is empty, read the first 50 segments to identify speakers and update metadata.guests before proceeding.
   c. NEVER attribute quotes to hosts/interviewers (Lex Fridman, Chris Anderson, Ezra Klein, Cleo Abram, Harry Stebbings, Dwarkesh Patel, Lenny Rachitsky, etc.) or use generic names (Guest Contributor, Panel Speaker, Unknown).
   d. Search segments for risk signal keywords:
      - Alarm/danger: existential, extinction, destroy, catastrophic, doom, wipe out, end of humanity, lose control, misaligned, uncontrollable, arms race, bioweapon, p(doom), could all lose, resist being shut down
      - Optimism/safety: benefit, cure, abundance, best thing, golden age, solvable, manageable, overstated, overblown, not as dangerous, flourish
      - Risk estimates: percent chance, probability, explicit percentages (1%, 5%, 10%, 20%, 50/50)
   c. Read surrounding segments for context.
   d. Extract the most quotable verbatim substring from a single segment (or short multi-segment window).
   e. Classify sentiment (alarm, concern, cautious_optimism, optimism, dismissal) and assign a score:
      - alarm: -1.0 to -0.6 (extinction, destroy humanity, wipe us out, could all lose)
      - concern: -0.6 to -0.2 (percent chance of catastrophic, could go wrong, serious risk)
      - cautious_optimism: -0.2 to 0.2 (risk + solvable/manageable/hopeful)
      - optimism: 0.2 to 0.6 (best thing, cure diseases, abundance, without caveats)
      - dismissal: 0.6 to 1.0 (doomers are wrong, overstated, not a real risk)
   f. Assign themes from: existential_risk, alignment_failure, loss_of_control, bioweapons, power_concentration, arms_race, job_displacement, consciousness_rights, safety_solvable, net_positive, regulation_needed, precautionary_principle
   g. Set is_builder=true for people directly building frontier AI (Amodei, Altman, Hassabis, Huang, Sutskever, Suleyman, Nadella, etc.) vs. commentators/academics (Harari, Tegmark, Bengio).
   h. Each signal follows this schema:
      {
        \"id\": \"risk-{video_id}-{timestamp_seconds}\",
        \"quote\": \"Verbatim text from transcript segment\",
        \"quote_context\": \"One-sentence editorial summary\",
        \"sentiment\": \"alarm|concern|cautious_optimism|optimism|dismissal\",
        \"sentiment_score\": -0.8,
        \"themes\": [\"existential_risk\", ...],
        \"person\": { \"name\": \"...\", \"role\": \"...\", \"company\": \"...\", \"is_builder\": true },
        \"source\": { \"video_id\": \"...\", \"url\": \"...\", \"title\": \"...\", \"channel\": \"...\", \"upload_date\": \"...\", \"timestamp_seconds\": 784, \"timestamp_display\": \"13:04\", \"timestamp_url\": \"...&t=784s\" },
        \"extracted_date\": \"$(date '+%Y-%m-%d')\",
        \"note_path\": \"vault/interviews/...\",
        \"verified\": false,
        \"verified_date\": null
      }
   i. Run: python3 scripts/verify-risk-signals.py --video-id VIDEO_ID --strict
      This checks BOTH quote verbatim accuracy AND speaker attribution.
      Fix any failures before continuing.
   j. Run: python3 scripts/verify-speakers.py --video-id VIDEO_ID --strict
      This independently confirms speaker names match transcript metadata.guests.
      Fix any failures before continuing.
   k. Append verified signals to data/risk-signals.json.
3. After all interviews are processed:
   a. Update data/processed.json with risk_signals_count for each video entry.
   b. Add a '## Risk Signals' table section to each interview note that has signals.
   c. Regenerate vault/visualizations/dead-or-alive.html with the updated data.

IMPORTANT RULES:
- The 'quote' field MUST be a verbatim substring from the transcript segments. Do NOT paraphrase, summarize, or editorialize.
- Speaker attribution MUST match metadata.guests from the transcript JSON. NEVER guess speakers from video titles.
- NEVER attribute quotes to hosts/interviewers or use generic names like 'Guest Contributor'.
- Prefer short distinctive phrases from single segments.

Work autonomously. Follow CLAUDE.md instructions. Do not ask questions."

echo ""
echo "Risk signal extraction completed at $(date '+%Y-%m-%d %H:%M:%S')"
echo "============================================"
