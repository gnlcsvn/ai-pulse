# AI Pulse - Autonomous Interview Scanner

## Project Purpose
Automatically discover, download, transcribe, and summarize state-of-the-art AI interviews from YouTube. Output goes to an Obsidian vault as markdown notes. Every quote, data point, and key takeaway is linked to its exact timestamp in the source video so the reader can verify anything with one click.

## How This Agent Is Invoked
A cron job runs `scripts/run.sh` which invokes Claude Code with `--print` mode pointing at this project. The agent should execute the full pipeline described below autonomously.

## Core Principle: Source Verification
Everything in the output must be traceable back to the original video. The reader should never have to wonder "did they really say that?" - they click the timestamp link and hear it themselves. This means:
- Whisper transcripts are always saved in **JSON format** (with per-segment start/end times)
- Every quote, data point, and key takeaway in the Obsidian note gets a `[▶ M:SS](youtube-url&t=Xs)` link

---

## Pipeline Steps

### Step 1: Discover New Videos
Search YouTube for recent AI interviews using `yt-dlp` search. Use the pipe-delimited format for easy parsing:

```bash
yt-dlp --flat-playlist --print "%(id)s | %(title)s | %(upload_date)s | %(duration)s | %(channel)s" "ytsearch30:AI interview 2026"
yt-dlp --flat-playlist --print "%(id)s | %(title)s | %(upload_date)s | %(duration)s | %(channel)s" "ytsearch20:artificial intelligence CEO interview"
yt-dlp --flat-playlist --print "%(id)s | %(title)s | %(upload_date)s | %(duration)s | %(channel)s" "ytsearch20:AI leader interview podcast"
```

Also check the specific channels listed in `config/sources.json` for their latest uploads:
```bash
yt-dlp --flat-playlist --print "%(id)s | %(title)s | %(upload_date)s | %(duration)s | %(channel)s" --playlist-end 5 "https://www.youtube.com/@CHANNEL_HANDLE/videos"
```

**Important**: Read `config/topics.md` for current search terms, people/companies of interest, and `config/sources.md` for tracked channels.

### Step 2: Filter & Deduplicate
- Read `data/processed.json` to check which video IDs have already been processed
- Skip any video already in processed.json
- From the remaining videos, evaluate relevance by title and channel:
  - INCLUDE: Interviews, podcasts, talks, fireside chats with AI company leaders, researchers, or engineers
  - INCLUDE: Videos featuring people from OpenAI, Anthropic, Google DeepMind, Meta AI, Mistral, xAI, NVIDIA, Microsoft AI, Cohere, Stability AI, Runway, Midjourney, etc.
  - INCLUDE: Videos discussing frontier AI models, AGI, AI safety, AI regulation, AI breakthroughs
  - EXCLUDE: Tutorials, how-to guides, product reviews, AI tool demos, AI news compilations without interviews
  - EXCLUDE: Videos shorter than 5 minutes or longer than 2 hours
  - EXCLUDE: Videos with `upload_date` older than 30 days from the current run date
  - EXCLUDE: Non-English content (unless from major AI figures)
- Select the top 3 most relevant videos to process in this run (to keep runs manageable)

### Step 3: Download Audio
For each selected video, download audio only:

```bash
yt-dlp -x --audio-format mp3 --audio-quality 3 -o "data/audio/%(id)s.%(ext)s" "https://www.youtube.com/watch?v=VIDEO_ID"
```

Also grab metadata:
```bash
yt-dlp --print-json --skip-download "https://www.youtube.com/watch?v=VIDEO_ID" > "data/audio/VIDEO_ID.info.json"
```

### Step 4: Transcribe (with timestamps and metadata)
Use mlx-whisper (Apple Silicon optimized) to transcribe each audio file. The script outputs both JSON (with per-segment timestamps and full metadata) and TXT in one call. **Always pass metadata** so the transcript is self-contained and reusable:

```bash
python3 scripts/transcribe.py "data/audio/VIDEO_ID.mp3" -l en \
  --video-id "VIDEO_ID" \
  --title "Full Video Title" \
  --channel "Channel Name" \
  --upload-date "YYYY-MM-DD" \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --duration "87m" \
  --guests "Guest Name 1, Guest Name 2"
```

This produces files named `YYYY-MM-DD_slugified-title.json` and `.txt`:
- `data/transcripts/YYYY-MM-DD_slugified-title.json` with metadata and segments:
  ```json
  {
    "metadata": {
      "video_id": "VIDEO_ID",
      "url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "title": "Full Video Title",
      "channel": "Channel Name",
      "upload_date": "YYYY-MM-DD",
      "duration": "87m",
      "guests": ["Guest Name 1"],
      "transcribed_date": "YYYY-MM-DD",
      "whisper_model": "mlx-community/whisper-large-v3-turbo"
    },
    "language": "en",
    "text": "full transcript text...",
    "segments": [
      {"id": 0, "start": 75.0, "end": 82.0, "text": "...the actual words spoken..."}
    ]
  }
  ```
- `data/transcripts/YYYY-MM-DD_slugified-title.txt` with the plain text

The default model is `mlx-community/whisper-large-v3-turbo` (better quality than the old `small` model and faster on Apple Silicon). Transcripts are kept permanently and should never be deleted.

### Step 5: Extract Key Facts & Generate Obsidian Note

**Step 5a: Read both transcripts**
Read `data/transcripts/VIDEO_ID.txt` for the full text and `data/transcripts/VIDEO_ID.json` for timestamp data.

**Step 5b: Find timestamps for key content**
For every quote, data point, and key takeaway you want to include, search the JSON segments for the matching text. Use a lowercase substring match on `segment.text`. The timestamp is `segment.start` in seconds. Convert to `M:SS` for display and use raw seconds for the YouTube `&t=` parameter.

Example: to find when "800 million monthly active users" was said, search segments for "800 million" → find `start: 325.0` → format as `[▶ 5:25](https://www.youtube.com/watch?v=VIDEO_ID&t=325s)`.

**Step 5b-ii: Extract predictions**
Scan the transcript for concrete, specific, falsifiable predictions. Look for:
- Timeframe language ("by 2030", "in 3 years", "within a decade", "next 5 years")
- Prediction verbs ("will", "expect", "predict", "my hunch is", "I think we'll see")
- Confidence qualifiers ("90% probability", "50/50", "almost certain", "I'd bet")
- AGI/ASI timelines, economic forecasts, tech milestones, job displacement, company/product predictions, regulation forecasts
- Skip vague aspirational statements — only include specific, verifiable/falsifiable claims

**CRITICAL: Timeframe year assignment rules**
The `timeframe.raw` field must contain ONLY the verbatim words from the transcript — never add editorial annotations like "(implied near-term)" or "(implied 2026-2027)".

Only assign `earliest_year`/`latest_year`/`midpoint_year` when the speaker explicitly states one of:
- **An explicit year**: "by 2030", "before 2035" → assign those years
- **A calculable relative timeframe**: "in 3 years", "within 5 years", "within a decade", "next 10 years" → calculate from `prediction_date` (see below)
- **A named decade**: "end of the decade", "by the 2030s" → assign the appropriate range
- **"End of this year"**, **"next year"** → calculate from `prediction_date`

Set all three year fields to `null` when the speaker uses:
- Vague language: "soon", "eventually", "at some point", "in the near term", "in the long term", "not long from now", "in the future"
- Conditional framing: "when X happens", "once we get to...", "if Y continues"
- No temporal language at all (just a directional claim like "AI will replace X")
- Current observations: "is happening now", "we're already seeing"

Predictions with null years are still valuable and should be extracted — they just won't appear on the timeline visualization. The interview markdown notes show all predictions regardless of whether they have dates.

For each prediction, create an entry following this schema:
```json
{
  "id": "pred-{video_id}-{timestamp_seconds}",
  "prediction": "What was predicted (concise summary)",
  "category": "AGI timeline | coding automation | economic impact | job displacement | robotics | compute infrastructure | AI safety incident | product/company | regulation | other",
  "person": { "name": "Speaker Name", "role": "Their Role", "company": "Their Company" },
  "timeframe": { "raw": "exact phrasing from transcript (verbatim, no editorial notes)", "earliest_year": 2027, "latest_year": 2030, "midpoint_year": 2028 },
  "confidence": { "raw": "exact phrasing or null", "level": "high|medium|low|speculative|unstated", "percentage": 90 },
  "source": {
    "video_id": "VIDEO_ID",
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "title": "Video Title",
    "channel": "Channel Name",
    "upload_date": "YYYY-MM-DD",
    "prediction_date": "YYYY-MM-DD",
    "timestamp_seconds": 841,
    "timestamp_display": "14:01",
    "timestamp_url": "https://www.youtube.com/watch?v=VIDEO_ID&t=841s"
  },
  "extracted_date": "YYYY-MM-DD",
  "note_path": "vault/interviews/YYYY-MM-DD_slug.md"
}
```

**`prediction_date` rules:**
- Default `prediction_date` to `upload_date` (most videos are published the same day or within days of recording)
- Override when evidence exists in the video title, description, or transcript (e.g., "TED2025" in the title → use the event date, "recorded in January" in the transcript → use that month)
- Use `prediction_date` (not `upload_date`) when calculating years for relative timeframes like "in 3 years", "within 5 years", "next year", "end of this year"

Find the exact timestamp for each prediction by searching the JSON segments (lowercase substring match). If no explicit predictions are found, that's fine — not every interview contains them.

**Step 5b-iii: Verify prediction timestamps and speaker attribution**
After extracting predictions for a video, verify each one before saving:

1. **`timeframe.raw` and `confidence.raw` MUST be verbatim substrings** copied directly from the transcript — never paraphrased, summarized, or editorialized. You must be able to find the exact string via case-insensitive substring search in the transcript segments.
2. **Derive `timestamp_seconds` from the transcript match, not from memory.** For each prediction, search the JSON segments for `timeframe.raw` as a case-insensitive substring. Use the matching segment's `start` time as `timestamp_seconds`. If the text spans a segment boundary, use the first segment's `start`.
3. **If a raw text string cannot be found verbatim in any segment** (single or multi-segment window), the text was paraphrased. Either fix it to the exact wording from the transcript or do not include the prediction.
4. **Speaker attribution MUST match `metadata.guests`** — see Speaker Identification Rules above. The `person.name` must be a guest listed in the transcript metadata, NOT a host/interviewer, and NOT a generic name.
5. **Post-processing gate:** After saving predictions for a video, run `python3 scripts/verify-predictions.py --video-id VIDEO_ID --strict`. This MUST pass with 0 paraphrased, 0 ambiguous, AND 0 speaker failures before proceeding to the next video. Fix any failures before continuing.

**Common mistakes to avoid** (discovered from audit of 277 predictions):
- **DO NOT use `...` (ellipsis) to stitch together phrases from different segments.** Pick one segment's text or use a short distinctive phrase from a single segment.
- **DO NOT add editorial notes in parentheses** like `"(implied near-term)"` or `"(no explicit timeframe)"`. If there's no timeframe language, set `timeframe.raw` to `null`.
- **DO NOT clean up Whisper transcription artifacts.** If the transcript says `"by the end of this, end of this year"` (stutter), the raw field must say that too, not `"by the end of this year"`.
- **DO NOT use generic phrases as raw text** like `"next year"` or `"I think"` if they appear many times in the transcript. Pick a longer, more distinctive substring that uniquely identifies the prediction.
- **Prefer short, distinctive substrings** from a single segment over long multi-segment reconstructions. A 5-word phrase from one segment is better than a 30-word reconstruction across 8 segments.

**CRITICAL: Speaker Identification Rules (applies to predictions, risk signals, and all quotes)**

Before extracting any predictions or risk signals, identify speakers deterministically:

1. **Read `metadata.guests` from the transcript JSON** — this is the ground truth for who the speakers are. NEVER rely on the video title or channel name to identify speakers (e.g., "Godfather of AI" could be Hinton OR Bengio).
2. **Verify the speaker name appears in the transcript intro** (first 50 segments). Speakers are typically introduced early in the video.
3. **Only attribute quotes to people listed in `metadata.guests`**. If `metadata.guests` is empty, populate it first by reading the transcript intro before extracting anything.
4. **Never attribute quotes to hosts/interviewers** unless they are AI principals making substantive claims about their own work. Known hosts to exclude: Lex Fridman, Chris Anderson, Ezra Klein, Cleo Abram, Harry Stebbings, Dwarkesh Patel, Lenny Rachitsky, Zanny Minton Beddoes, Francine Lacqua, Emma Tucker, Roula Khalaf, Nikhil Kamath, Ross Douthat, Andrew Ross Sorkin, Kara Swisher, Scott Pelley, Erik Torenberg, Packy McCormick.
5. **Never use generic/anonymous attributions** like "Guest Contributor", "Panel Speaker", "Audience Member", "Unknown". If you cannot identify the speaker, do not extract the quote.
6. **For multi-speaker panels/interviews**, pay close attention to conversational context to attribute quotes to the correct speaker. When in doubt, skip the quote.
7. **Post-processing gate**: After extracting predictions/risk signals for a video, run `python3 scripts/verify-speakers.py --video-id VIDEO_ID --strict`. This MUST pass before proceeding.

**Step 5b-iv: Extract risk signals**
Scan the transcript for statements about existential risk, catastrophic AI outcomes, or AI safety sentiment. Look for:
- **Alarm/danger keywords:** existential, extinction, destroy, catastrophic, doom, wipe out, end of humanity, lose control, misaligned, uncontrollable, arms race, bioweapon, p(doom), could all lose, resist being shut down
- **Optimism/safety keywords:** benefit, cure, abundance, best thing, golden age, solvable, manageable, overstated, overblown, not as dangerous, flourish
- **Risk estimates:** percent chance, probability, explicit percentages (1%, 5%, 10%, 20%, 50/50)

For each risk signal, extract a verbatim quote from the transcript segments and classify it:

| Sentiment | Score range | Signal |
|---|---|---|
| `alarm` | -1.0 to -0.6 | "extinction", "destroy humanity", "wipe us out", "could all lose" |
| `concern` | -0.6 to -0.2 | "percent chance of catastrophic", "could go wrong", "serious risk" |
| `cautious_optimism` | -0.2 to 0.2 | Risk acknowledgment + "solvable", "manageable", "hopeful" |
| `optimism` | 0.2 to 0.6 | "best thing", "cure diseases", "abundance", without caveats |
| `dismissal` | 0.6 to 1.0 | "doomers are wrong", "overstated", "not a real risk" |

Assign themes from: `existential_risk`, `alignment_failure`, `loss_of_control`, `bioweapons`, `power_concentration`, `arms_race`, `job_displacement`, `consciousness_rights`, `safety_solvable`, `net_positive`, `regulation_needed`, `precautionary_principle`

Set `is_builder=true` for people directly building frontier AI (Amodei, Altman, Hassabis, Huang, Sutskever, Suleyman, Nadella) vs. commentators/academics (Harari, Tegmark, Bengio).

Save each signal to `data/risk-signals.json` following the schema (see `data/risk-signals.json` for the full structure). The `quote` field MUST be a verbatim substring — same rules as `timeframe.raw` in predictions.

**Step 5b-v: Verify risk signals**
After extracting risk signals for a video, run `python3 scripts/verify-risk-signals.py --video-id VIDEO_ID --strict`. This MUST pass with 0 paraphrased, 0 ambiguous, AND 0 speaker failures before proceeding. The `--strict` flag now also runs speaker attribution checks automatically.

**Step 5c: Write the Obsidian note**
Create a structured note at `vault/interviews/YYYY-MM-DD_video-title-slug.md`:

```markdown
---
date: YYYY-MM-DD
source: YouTube
video_id: VIDEO_ID
url: https://www.youtube.com/watch?v=VIDEO_ID
channel: Channel Name
title: Full Video Title
guests: [Guest Name 1, Guest Name 2]
topics: [topic1, topic2, topic3]
duration: XhYm
prediction_date: YYYY-MM-DD
processed_date: YYYY-MM-DD
predictions_count: 0
---

# Title of Interview

## Guests
- **Guest Name** - Role, Company

## Key Takeaways
1. First major insight or announcement [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs)
2. Second major insight [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs)
(list 5-10 key takeaways, each with a timestamp link)

## Notable Quotes
> "Exact quote from transcript" - Speaker Name [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs)

> "Another notable quote" - Speaker Name [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs)

## Data Points & Numbers
| Data Point | Value | Source Timestamp |
|---|---|---|
| Description | **Value** | [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs) |

## Predictions
| Prediction | Timeframe | Confidence | Source |
|---|---|---|---|
| Description of prediction | Timeframe phrasing | Confidence level | [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs) |

(If no explicit predictions found: "No explicit predictions identified in this interview.")

## Risk Signals
| Quote | Sentiment | Score | Themes | Source |
|---|---|---|---|---|
| "Verbatim quote" | alarm/concern/etc | -0.8 | themes | [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs) |

(If no risk signals found: "No explicit risk signals identified in this interview.")

## Topics Discussed
- **Topic Name**: Brief summary [▶ M:SS](https://www.youtube.com/watch?v=VIDEO_ID&t=Xs)

## Summary
A 3-5 paragraph summary of the interview covering the main discussion points, key announcements, and notable opinions expressed.

## Connections
- [[Person Name]]
- [[Company Name]]
- [[Related Interview]]
```

### Step 6: Update Tracking
After processing each video, add its ID to `data/processed.json`:

The entry should include:
```json
{
  "video_id": "ID",
  "title": "Full Title",
  "channel": "Channel Name",
  "upload_date": "YYYY-MM-DD",
  "processed_date": "YYYY-MM-DD",
  "status": "success",
  "note_path": "vault/interviews/YYYY-MM-DD_slug.md",
  "transcript_path": "data/transcripts/VIDEO_ID.json",
  "predictions_count": 0,
  "risk_signals_count": 0
}
```

Also update `last_run` and `total_processed` in the top-level object.

Additionally, append any extracted predictions to `data/predictions.json`. Use the deterministic ID format `pred-{video_id}-{timestamp_seconds}` to avoid duplicates — if an ID already exists, skip it.

Additionally, append any extracted risk signals to `data/risk-signals.json`. Use the deterministic ID format `risk-{video_id}-{timestamp_seconds}` to avoid duplicates — if an ID already exists, skip it.

### Step 7: Generate Daily Summary
If any videos were processed, create/update the daily summary at `vault/summaries/YYYY-MM-DD.md`:

```markdown
---
date: YYYY-MM-DD
type: daily-summary
videos_processed: N
---

# AI Pulse - YYYY-MM-DD

## Videos Processed Today
- [[Interview Note 1]] - Brief one-line summary
- [[Interview Note 2]] - Brief one-line summary

## Top Insights
1. Most important insight across all videos
2. Second most important
3. Third most important

## Trending Topics
- Topic 1 (mentioned in N videos)
- Topic 2 (mentioned in N videos)
```

### Step 8: Update Predictions Timeline
If any predictions were extracted during this run, regenerate `vault/visualizations/predictions-timeline.html` by reading `data/predictions.json` and inlining the predictions data as a JavaScript constant. The HTML is a self-contained D3.js visualization (dark theme) with:
- Filter bar (by category, by person)
- Interactive SVG timeline: Y-axis = person, X-axis = year, range bars for predictions
- Consensus band for AGI timeline predictions (25th-75th percentile)
- Hover tooltips with prediction details, click to open YouTube at timestamp
- Sortable predictions table
- Category breakdown chart

### Step 8b: Update Dead or Alive Visualization
If any risk signals were extracted during this run, regenerate `vault/visualizations/dead-or-alive.html` by reading `data/risk-signals.json` and inlining the signals data as a JavaScript constant (replacing the `SIGNALS_DATA` assignment). The HTML is a self-contained D3.js visualization with:
- Hero stat: "X of Y AI builders have publicly warned their technology could cause catastrophic harm"
- Spectrum bar with person dots positioned by average sentiment score
- Person cards with top quotes, sentiment labels, and share buttons
- Interactive dot plot: X-axis = sentiment score, Y-axis = person, colored by theme
- Quote wall: masonry grid of shareable quote cards
- Sentiment distribution donut, theme frequency bars, builder vs. commentator comparison, rhetoric over time
- Sortable data table
- Share mechanics: clipboard copy + Web Share API + Twitter intent

---

## YouTube Link Health Check
Periodically (at least once per run), verify that processed YouTube videos are still available. For each video in `data/processed.json`:

```bash
yt-dlp --skip-download --print "%(availability)s" "https://www.youtube.com/watch?v=VIDEO_ID"
```

If a video returns an error or shows as unavailable/private/removed:
- Add `"link_status": "dead"` and `"link_checked": "YYYY-MM-DD"` to the video's entry in `processed.json`
- Do NOT delete the video's data (transcript, note, predictions) — the content is still valuable
- Add a notice at the top of the Obsidian note: `> ⚠️ **Source video unavailable** as of YYYY-MM-DD. The original transcript and all timestamps are preserved below.`
- Log the finding in the daily summary

For videos that are still available, update `"link_checked": "YYYY-MM-DD"` to track when they were last verified. Focus checks on older videos first (those with the oldest or missing `link_checked` date).

---

## Error Handling
- If `yt-dlp` fails on a video, skip it and log the error. Do not retry.
- If `transcribe.py` fails, skip the video.
- If a transcript is empty or very short (<100 words), skip the video.
- Always update `data/processed.json` even for failed videos (mark them with `"status": "failed"` and a reason).

## Cleanup
- After successful processing, delete audio files from `data/audio/` to save disk space.
- Keep both JSON and TXT transcripts in `data/transcripts/` permanently (needed for verification and future re-processing).

## File Naming Conventions
- Slugify video titles: lowercase, hyphens instead of spaces, remove special characters, max 60 chars
- Date prefix: YYYY-MM-DD (use the video's upload date, not the processing date)
- Example: `2026-02-12_sam-altman-on-gpt5-and-agi.md`

## Project Structure
```
ai-pulse/
├── CLAUDE.md                   # This file - agent instructions
├── scripts/
│   ├── run.sh                  # Cron entry point (invokes Claude Code)
│   ├── reprocess-predictions.sh # Batch re-extract predictions from all transcripts
│   ├── extract-risk-signals.sh  # Batch extract risk signals from all transcripts
│   ├── verify-risk-signals.py   # Verify risk signal quotes against transcripts
│   └── verify-speakers.py       # Verify speaker attribution against transcript metadata
├── config/
│   ├── topics.md               # Search terms, people, companies, filters (editable markdown)
│   └── sources.md              # Tracked YouTube channels (editable markdown)
├── data/
│   ├── processed.json          # Tracks all processed videos
│   ├── predictions.json        # Structured predictions database
│   ├── risk-signals.json       # Structured risk signals database (existential risk quotes)
│   ├── queue.json              # Videos queued for processing (pick from top)
│   ├── transcripts/            # Whisper outputs (.json with timestamps, .txt for reading)
│   └── audio/                  # Temporary audio files (deleted after processing)
└── vault/                      # Obsidian vault
    ├── interviews/             # Individual interview notes with timestamp links
    ├── summaries/              # Daily digests
    └── visualizations/         # Interactive HTML visualizations (predictions timeline, dead-or-alive, etc.)
```

## Important Notes
- Process a maximum of 3 videos per run to keep execution time reasonable
- Prefer recent videos (last 7 days) over older ones
- Prefer interviews with well-known AI figures over unknown channels
- The Obsidian vault is at `vault/` - all markdown goes there
- All paths are relative to the project root `/Users/gian-lucasavino/Documents/Claude/ai-pulse/`
