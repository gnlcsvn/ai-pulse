# AI Pulse

Autonomous pipeline that discovers, transcribes, and summarizes AI leader interviews from YouTube. Every quote, data point, and prediction is linked to its exact source timestamp so you can verify anything with one click.

Output goes to an Obsidian vault as structured markdown notes.

## How It Works

A daily cron job invokes Claude Code in `--print` mode, which autonomously:

1. **Discovers** new AI interviews via `yt-dlp` search and tracked channels
2. **Filters** by relevance (AI leaders, frontier research, company announcements)
3. **Downloads** audio and transcribes with `mlx-whisper` (Apple Silicon optimized)
4. **Extracts** key takeaways, quotes, data points, and predictions — each with a `[▶ timestamp](youtube-link)` source link
5. **Generates** Obsidian markdown notes and an interactive predictions timeline

## Predictions Timeline

92 concrete, falsifiable predictions extracted from 12 interviews with AI leaders including Dario Amodei, Elon Musk, Mustafa Suleyman, Boris Cherny, and others.

Interactive D3.js visualization at `vault/visualizations/predictions-timeline.html`:
- Filter by category (AGI timeline, coding automation, economic impact, etc.) and person
- Range bars showing prediction timeframes with consensus bands
- Click any prediction to jump to the exact moment in the source video
- Sortable table with all 92 predictions

**To view locally:**
```bash
python3 -m http.server 8000
# Open http://localhost:8000/vault/visualizations/predictions-timeline.html
```

## Project Structure

```
ai-pulse/
├── CLAUDE.md                      # Agent instructions (full pipeline spec)
├── scripts/
│   ├── run.sh                     # Cron entry point
│   ├── transcribe.py              # mlx-whisper transcription
│   └── reprocess-predictions.sh   # Batch re-extract predictions
├── config/
│   ├── topics.md                  # Search terms, people, companies
│   └── sources.md                 # Tracked YouTube channels
├── data/
│   ├── processed.json             # Video tracking database
│   ├── predictions.json           # 92 structured predictions
│   ├── queue.json                 # Videos queued for processing
│   └── transcripts/               # Whisper JSON + TXT (12 interviews)
└── vault/                         # Obsidian vault
    ├── interviews/                # 12 interview notes with timestamp links
    ├── summaries/                 # Daily digests
    └── visualizations/            # Interactive HTML (predictions timeline)
```

## Requirements

- macOS with Apple Silicon (for mlx-whisper)
- `yt-dlp`, `ffmpeg`, `python3`, `claude` CLI
- `mlx-whisper` (`pip install mlx-whisper`)

## Stats

| Metric | Value |
|--------|-------|
| Interviews processed | 12 |
| Predictions extracted | 92 |
| AGI timeline predictions | 14 |
| Median predicted AGI year | 2030 |
| Transcript hours | ~20h |
