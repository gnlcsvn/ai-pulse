# AI Pulse

An autonomous pipeline that discovers, transcribes, and analyzes AI leader interviews from YouTube — plus a static website that makes the extracted data explorable and verifiable.

## The Website

**https://gnlcsvn.github.io/ai-pulse/**

A static site built with Vite, serving two interactive D3.js visualizations:

- **Predictions Timeline** — 273 concrete, falsifiable predictions from 28 AI leaders (Dario Amodei, Elon Musk, Sam Altman, Jensen Huang, and others). Filter by category and person, hover for details, click any dot to jump to the exact moment in the source video.
- **Dead or Alive** — Risk signals extracted from the same interviews: what the people building AI say about its dangers, mapped on a spectrum from alarm to dismissal.

Every data point links to a timestamped YouTube URL so you can verify anything with one click.

## The Repository

The repo contains two things:

### 1. Data pipeline (`scripts/`, `data/`, `config/`)

A cron job invokes Claude Code in `--print` mode, which autonomously:

1. **Discovers** new AI interviews via `yt-dlp` search and tracked channels
2. **Filters** by relevance (AI leaders, frontier research, company announcements)
3. **Downloads** audio and transcribes with `mlx-whisper` (Apple Silicon optimized)
4. **Extracts** predictions, risk signals, key takeaways, and quotes — each traced to its source timestamp
5. **Verifies** extracted data against transcripts (speaker attribution, verbatim quotes, timestamp accuracy)
6. **Generates** Obsidian markdown notes for each interview

### 2. Static site (`site/`)

A multi-page Vite app that reads the pipeline's JSON output and renders it as interactive visualizations. Deployed to GitHub Pages.

```bash
cd site
./build.sh                  # sync data from pipeline
npm run dev                 # develop locally at localhost:5173
npm run build && npm run deploy   # build and push to GitHub Pages
```

## Project Structure

```
ai-pulse/
├── CLAUDE.md                      # Agent instructions (full pipeline spec)
├── scripts/
│   ├── run.sh                     # Cron entry point
│   ├── transcribe.py              # mlx-whisper transcription
│   ├── verify-predictions.py      # Verify prediction quotes against transcripts
│   ├── verify-risk-signals.py     # Verify risk signal quotes against transcripts
│   └── verify-speakers.py         # Verify speaker attribution
├── config/
│   ├── topics.md                  # Search terms, people, companies
│   └── sources.md                 # Tracked YouTube channels
├── data/
│   ├── processed.json             # Video tracking database (38 videos)
│   ├── predictions.json           # 273 structured predictions
│   ├── risk-signals.json          # 283 risk signals
│   └── transcripts/               # Whisper JSON + TXT
├── site/                          # Static website (Vite + D3.js)
│   ├── index.html                 # Landing page
│   ├── predictions/index.html     # Predictions timeline
│   ├── dead-or-alive/index.html   # Risk signals visualization
│   ├── src/                       # JS modules (shared/, predictions/, dead-or-alive/)
│   └── public/data/               # JSON data synced from pipeline
└── vault/                         # Obsidian vault
    ├── interviews/                # 38 interview notes with timestamp links
    └── summaries/                 # Daily digests
```

## Requirements

- macOS with Apple Silicon (for mlx-whisper)
- `yt-dlp`, `ffmpeg`, `python3`, `claude` CLI
- `mlx-whisper` (`pip install mlx-whisper`)
- Node.js (for the site)

## Stats

| Metric | Value |
|--------|-------|
| Interviews processed | 38 |
| Predictions extracted | 273 |
| Risk signals extracted | 283 |
| People tracked | 28 |
| AGI timeline predictions | 26 |
| Median predicted AGI year | 2029 |
