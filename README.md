# AI News YouTube — Full Replication Guide

> **Zero-cost, never-stop AI news channel** that discovers, verifies, ranks, scripts, voices, and uploads **2 videos daily** to YouTube — fully autonomous.

This guide walks you from an empty folder to a fully automatic pipeline that produces 2 YouTube videos per day with Telegram alerts — no human intervention needed.

---

## Table of Contents

1. [What This System Does](#what-this-system-does)
2. [Prerequisites](#prerequisites)
3. [Step 1: Clone & Install](#step-1-clone--install)
4. [Step 2: Get All API Keys (Free)](#step-2-get-all-api-keys-free)
5. [Step 3: Configure Environment](#step-3-configure-environment)
6. [Step 4: YouTube OAuth Setup](#step-4-youtube-oauth-setup)
7. [Step 5: Telegram Bot Setup](#step-5-telegram-bot-setup)
8. [Step 6: Seed News Sources](#step-6-seed-news-sources)
9. [Step 7: Test Run (Single Video)](#step-7-test-run-single-video)
10. [Step 8: Set Up Automatic 2 Videos/Day](#step-8-set-up-automatic-2-videosday)
11. [Step 9: Verify Everything Works](#step-9-verify-everything-works)
12. [Architecture & How It Works](#architecture--how-it-works)
13. [Pipeline Agents Explained](#pipeline-agents-explained)
14. [Configuration Reference](#configuration-reference)
15. [Telegram Notifications](#telegram-notifications)
16. [YouTube Upload Details](#youtube-upload-details)
17. [Database Schema](#database-schema)
18. [Troubleshooting](#troubleshooting)
19. [File Structure](#file-structure)

---

## What This System Does

Every day, automatically:

```
1. COLLECT    — Fetches articles from 76+ news sources across 15+ countries
2. DETECT     — Identifies trending topics using embeddings
3. VERIFY     — Fact-checks articles using LLM + content moderation
4. RANK       — Picks the SINGLE BEST article for a YouTube Short
5. SEO        — Generates optimized title, description, tags, hashtags
6. SCRIPT     — Writes a 45-59 second narration script (130-170 words)
7. REVIEW     — Quality-checks the script (auto-retries up to 3 times)
8. THUMBNAIL  — Generates an eye-catching thumbnail with AI image gen
9. NARRATE    — Converts script to speech with word-level captions
10. VIDEO     — Assembles Shorts video (1080x1920) with FFmpeg
11. UPLOAD    — Uploads to YouTube with metadata + thumbnail
12. ANALYTICS — Records run data to database
13. LEARN     — Self-improvement loop analyzes performance
```

**Result:** 2 YouTube Shorts videos published daily, Telegram alerts for every run.

---

## Prerequisites

| Requirement | Version | How to Check | Install If Missing |
|-------------|---------|--------------|-------------------|
| **Python** | 3.11+ | `python --version` | `winget install Python.Python.3.11` |
| **Git** | any | `git --version` | `winget install Git.Git` |
| **FFmpeg** | any | `ffmpeg -version` | `winget install Gyan.FFmpeg` |
| **GitHub CLI** | any | `gh --version` | `winget install GitHub.cli` |

**Optional (for local features):**
| Tool | Purpose | Install |
|------|---------|---------|
| Ollama | Local LLM fallback | `ollama.com` |
| Node.js 18+ | Dashboard | `winget install OpenJS.NodeJS` |

---

## Step 1: Clone & Install

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/ai-news-youtube.git
cd ai-news-youtube

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Mac/Linux)
source .venv/bin/activate

# Install all dependencies
pip install -e .
```

Verify installation:
```bash
python -c "import langgraph; import edge_tts; import httpx; print('All good!')"
```

---

## Step 2: Get All API Keys (Free)

You need **3 API keys** (all free). This takes about 10 minutes.

### 2a. Groq API Key (Required — LLM Inference)

1. Go to https://console.groq.com
2. Sign up / Sign in
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_`)
5. Save it — you'll need it in Step 3

**What it does:** Powers all AI reasoning — trend detection, fact verification, script writing, SEO optimization, quality review. Uses Llama 3.1 8B (fast) and Llama 3.3 70B (quality). Free tier: 30,000 requests/day.

### 2b. YouTube OAuth (Required — Video Upload)

1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. **Enable API:** Search for "YouTube Data API v3" → Enable
4. **Create OAuth credentials:**
   - Go to **APIs & Services** → **Credentials**
   - Click **Create Credentials** → **OAuth client ID**
   - Application type: **Desktop app**
   - Name: "AI News Pipeline"
   - Click **Create**
5. **Download** the `client_secrets.json` file
6. Save it as `config/client_secrets.json`:
   ```bash
   mkdir config
   # Move the downloaded file:
   move ~/Downloads/client_secrets.json config/client_secrets.json
   ```

**What it does:** Allows the pipeline to upload videos to your YouTube channel.

### 2c. Telegram Bot (Recommended — Alerts)

1. Open Telegram, search for **@BotFather**
2. Send `/newbot`
3. Name your bot (e.g., "AI News Pipeline")
4. Choose a username (e.g., "MyAINewsBot")
5. **Copy the bot token** (looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
6. **Send ANY message to your new bot** (this registers your chat ID)
7. Get your chat ID:
   - Open browser, visit: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   - Look for `"chat":{"id": 6786429335}` — that number is YOUR chat ID
   - ⚠️ **NOT the bot's ID from the token!** Your chat ID is always different.

**What it does:** Sends you alerts when pipeline starts, completes, or fails.

---

## Step 3: Configure Environment

```bash
# Copy the template
cp .env.example .env
```

Open `.env` and fill in your keys:

```env
# === REQUIRED ===
GROQ_API_KEY=gsk_your_groq_key_here

# === YOUTUBE UPLOAD ===
YOUTUBE_CLIENT_ID=your_client_id.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-your_client_secret
YOUTUBE_REFRESH_TOKEN=your_refresh_token

# === TELEGRAM (recommended) ===
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=6786429335

# === PIPELINE SETTINGS ===
VIDEOS_PER_DAY=2
PIPELINE_RUN_HOURS=6,14
AUTO_UPLOAD=true
REVIEW_BEFORE_UPLOAD=false
CONTENT_MODERATION_STRICT=true
MAX_ARTICLES_PER_RUN=50
TTS_ENGINE=edge-tts
TTS_VOICE=en-US-ChristopherNeural
IMAGE_PROVIDER=pollinations
```

> **Note:** You'll get the `YOUTUBE_REFRESH_TOKEN` in Step 4. For now, leave it blank and come back.

---

## Step 4: YouTube OAuth Setup

This step generates the refresh token needed for automatic uploads.

```bash
# Make sure config/ directory exists
mkdir config

# Run the OAuth flow (opens browser)
python scripts/auth_youtube.py
```

What happens:
1. A browser window opens
2. Sign in with your YouTube/Google account
3. Grant permission to upload videos
4. Token is saved to `config/youtube_token.json`
5. Script confirms your channel name

**Copy the refresh token to `.env`:**
```bash
# The script prints it. Or extract manually:
python -c "import json; t=json.load(open('config/youtube_token.json')); print(t['refresh_token'])"
```

Add to `.env`:
```
YOUTUBE_REFRESH_TOKEN=1//your_refresh_token_here
```

**Verify it works:**
```bash
python scripts/auth_youtube.py  # Should say "YouTube upload is now configured!"
```

---

## Step 5: Telegram Bot Setup

**Method 1 — Interactive script (easiest):**
```bash
python scripts/setup_telegram.py
```
Just paste your bot token — the script auto-detects your chat ID and sends a test message.

**Method 2 — Verify manually:**
```bash
python -c "
import httpx
token = 'YOUR_BOT_TOKEN'
chat_id = 'YOUR_CHAT_ID'
r = httpx.post(f'https://api.telegram.org/bot{token}/sendMessage', 
    json={'chat_id': chat_id, 'text': '✅ Pipeline alerts enabled!', 'parse_mode': 'HTML'})
print(f'Status: {r.status_code}')
"
```

You should see the message in Telegram instantly.

---

## Step 6: Seed News Sources

```bash
python scripts/seed_sources.py
```

This populates the database with **76+ news sources** from:
- 🇺🇸 USA (TechCrunch, NYT, CNN, Wired, Ars Technica, MIT Tech Review...)
- 🇬🇧 UK (BBC, Guardian, Independent, Telegraph)
- 🇮🇳 India (The Hindu, NDTV, Times of India, Indian Express...)
- 🇩🇪 Germany (Deutsche Welle, Spiegel)
- 🇫🇷 France (France24, Le Monde)
- 🇯🇵 Japan (NHK, Japan Times)
- 🇰🇷 Singapore (Channel News Asia)
- 🇨🇳 China (SCMP, China Daily)
- 🇦🇺 Australia (ABC, Sydney Morning Herald)
- 🇨🇦 Canada (CBC, Globe & Mail)
- 🇧🇷 Brazil (Folha)
- 🇿🇦 Africa (Daily Maverick, News24)
- + Science sources (Nature, Science Daily, Space.com)
- + Entertainment (Variety, Hollywood Reporter, ESPN)

---

## Step 7: Test Run (Single Video)

Before setting up automation, run once manually to verify everything works:

```bash
python scripts/run_pipeline.py --mode daily_news
```

**What to watch for:**
```
✅ "Fetching news from all sources..."     — Collector working
✅ "Found X trends"                         — Trend detection working
✅ "Verified X articles"                    — Fact-checking working
✅ "Selected: [category] Article Title"     — Best article picked
✅ "Script: 155 words, 52s"                — Script generated
✅ "Script approved (score: 8)"             — Quality review passed
✅ "Thumbnail: output/thumbnails/thumb_..." — Thumbnail created
✅ "Audio: output/audio/narration_..."      — TTS narration done
✅ "Video: output/videos/short_..."         — Video assembled
✅ "Uploaded: https://youtube.com/..."      — YouTube upload successful
```

**Check outputs:**
```bash
# Video file
dir output\videos\*.mp4

# Thumbnail
dir output\thumbnails\*.jpg

# Audio
dir output\audio\*.mp3
```

**Check Telegram:** You should receive a success notification with the article title and YouTube link.

**Check YouTube:** The video should appear on your channel.

---

## Step 8: Set Up Automatic 2 Videos/Day

### Option A: GitHub Actions (Recommended — Runs Forever)

This runs even when your computer is off. The pipeline executes on GitHub's servers.

**1. Authenticate GitHub CLI:**
```bash
gh auth login
```

**2. Set all 6 secrets:**
```bash
REPO="YOUR_USERNAME/ai-news-youtube"  # Replace with YOUR repo

gh secret set GROQ_API_KEY --body "gsk_your_key_here" --repo $REPO

gh secret set YOUTUBE_CLIENT_ID --body "your_client_id.apps.googleusercontent.com" --repo $REPO

gh secret set YOUTUBE_CLIENT_SECRET --body "GOCSPX-your_secret" --repo $REPO

gh secret set YOUTUBE_REFRESH_TOKEN --body "1//your_refresh_token" --repo $REPO

gh secret set TELEGRAM_BOT_TOKEN --body "123456789:ABCdef..." --repo $REPO

gh secret set TELEGRAM_CHAT_ID --body "6786429335" --repo $REPO
```

**3. Verify secrets are set:**
```bash
gh secret list --repo YOUR_USERNAME/ai-news-youtube
```

You should see all 6 secrets listed.

**4. Trigger a test run:**
```bash
gh workflow run daily_news.yml --repo YOUR_USERNAME/ai-news-youtube
```

**5. Watch the run:**
```bash
gh run list --repo $REPO --limit 5
gh run view --repo $REPO  # watch live
```

**What happens automatically:**
- **06:00 UTC daily** → Pipeline runs, produces 1 video
- **14:00 UTC daily** → Pipeline runs, produces 1 video
- **Telegram alerts** sent for each run
- **Artifacts** saved for 7 days on GitHub

### Option B: Local Scheduler (Your Computer Must Be On)

```bash
python scripts/scheduler.py
```

This runs forever in your terminal:
- Runs at 06:00 and 14:00 (configurable via `PIPELINE_RUN_HOURS`)
- If a run fails, the next run still happens
- 2-minute retry on failures, 5-minute wait on critical errors
- Daily API limit reset at midnight
- Press Ctrl+C to stop gracefully

**To run in background (Windows):**
```bash
# Use a screen/tmux session or run in a separate terminal
python scripts/scheduler.py
```

**To run in background (Linux/Mac):**
```bash
nohup python scripts/scheduler.py > scheduler.log 2>&1 &
```

---

## Step 9: Verify Everything Works

After the first automatic run, check all 3 outputs:

**1. YouTube Channel:**
- Visit your channel
- Should see 2 new Shorts videos

**2. Telegram:**
- Should have received start notification (🚀)
- Should have received completion notification (✅) with YouTube link
- If failed: should have received failure notification (❌) with error details

**3. Database:**
```bash
python -c "
import sqlite3
conn = sqlite3.connect('news_pipeline.db')
runs = conn.execute('SELECT id, status, videos_produced, videos_uploaded, started_at FROM pipeline_runs ORDER BY id DESC LIMIT 5').fetchall()
for r in runs:
    print(f'Run {r[0]}: {r[1]} | Videos: {r[2]} | Uploaded: {r[3]} | {r[4]}')
"
```

**4. GitHub Actions (if using):**
```bash
gh run list --repo $REPO --limit 5
```

---

## Architecture & How It Works

```
┌─────────────────────────────────────────────────────────────┐
│              NEVER-STOP SCHEDULER (2x/day)                  │
│                                                             │
│  Run 1: 06:00 UTC    Run 2: 14:00 UTC                      │
│       │                    │                                │
│       └────────────────────┘                                │
│                     │                                       │
│                     ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              LANGGRAPH PIPELINE                       │   │
│  │                                                      │   │
│  │  Collector → TrendDetector → Verifier → Ranker       │   │
│  │       → SEO → ScriptWriter ←→ Reviewer (loop)        │   │
│  │       → Thumbnail → Narrator → VideoAssembler        │   │
│  │       → Uploader → Analytics → Learner               │   │
│  └──────────────────────────────────────────────────────┘   │
│                     │                                       │
│                     ▼                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐       │
│  │  Groq API   │  │ Pollinations │  │  YouTube    │       │
│  │  (LLM free) │  │ (thumbnails) │  │  Data API   │       │
│  └─────────────┘  └──────────────┘  └─────────────┘       │
│                                                             │
│  NEVER STOPS. Each run is independent.                      │
│  Failure in one run → next run still happens.               │
└─────────────────────────────────────────────────────────────┘
```

**Key design principles:**
- **Run isolation:** Each pipeline run is a fresh state dict — no carryover from previous runs
- **Graceful degradation:** If LLM fails → template fallback. If thumbnail fails → solid color. If upload fails → saved locally
- **No cascading failures:** If one agent fails, the pipeline records the error and continues to the next scheduled time

---

## Pipeline Agents Explained

| # | Agent | What It Does | LLM Used |
|---|-------|-------------|----------|
| 1 | **Collector** | Fetches from 76+ RSS feeds, deduplicates, filters already-used articles | None (pure parsing) |
| 2 | **TrendDetector** | Analyzes articles, finds top 5 trending topics with velocity/impact/novelty scores | Groq Llama 3.1 8B |
| 3 | **Verifier** | Fact-checks each article, runs content moderation, blocks inappropriate content | Groq Llama 3.1 8B |
| 4 | **Ranker** | Picks the SINGLE BEST article for a YouTube Short based on viral potential | Groq Llama 3.1 8B |
| 5 | **SEO** | Generates optimized title (40 chars), description, 15 tags, 5 hashtags | Groq Llama 3.1 8B |
| 6 | **ScriptWriter** | Writes 45-59 second narration script (130-170 words) | Groq Llama 3.3 70B |
| 7 | **Reviewer** | Quality-checks script, auto-rejects if too long/bad, retries up to 3 times | Groq Llama 3.1 8B |
| 8 | **Thumbnail** | Generates AI image, adds vignette, category badge, title text, top banner | Pollinations.ai + Pillow |
| 9 | **Narrator** | Converts script to speech with word-by-word captions (ASS subtitles) | edge-tts |
| 10 | **Video** | Assembles 1080x1920 Shorts video with Ken Burns effect + live captions | FFmpeg |
| 11 | **Uploader** | Uploads to YouTube with sanitized metadata + thumbnail | YouTube Data API v3 |
| 12 | **Analytics** | Records pipeline run data to SQLite database | None |
| 13 | **Learner** | Analyzes performance patterns, saves insights for self-improvement | None |

**LLM Fallback Chain:** Groq → OpenRouter → Cerebras → Ollama (local) → Template (always works)

---

## Configuration Reference

### All Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ Yes | — | Groq API key (free at console.groq.com) |
| `YOUTUBE_CLIENT_ID` | ✅ For upload | — | Google Cloud OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | ✅ For upload | — | Google Cloud OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | ✅ For upload | — | OAuth refresh token (from auth_youtube.py) |
| `TELEGRAM_BOT_TOKEN` | Recommended | — | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Recommended | — | Your personal Telegram chat ID |
| `VIDEOS_PER_DAY` | — | `2` | Videos to produce daily (1-10) |
| `PIPELINE_RUN_HOURS` | — | `6,14` | Comma-separated UTC hours for runs |
| `AUTO_UPLOAD` | — | `false` | Auto-upload without review |
| `REVIEW_BEFORE_UPLOAD` | — | `true` | Pause for manual review |
| `CONTENT_MODERATION_STRICT` | — | `true` | Strict content filtering |
| `MAX_ARTICLES_PER_RUN` | — | `50` | Max articles to fetch |
| `TTS_ENGINE` | — | `edge-tts` | TTS engine (`edge-tts` or `piper`) |
| `TTS_VOICE` | — | `en-US-ChristopherNeural` | Voice name |
| `IMAGE_PROVIDER` | — | `pollinations` | Thumbnail service |
| `DATABASE_PATH` | — | `news_pipeline.db` | SQLite file path |
| `OPENROUTER_API_KEY` | — | — | Fallback LLM provider |
| `TOGETHER_API_KEY` | — | — | Fallback image generation |
| `TURSO_DATABASE_URL` | — | — | Cloud DB for dashboard |
| `TURSO_AUTH_TOKEN` | — | — | Cloud DB auth token |

### Schedule Configuration

```env
# Run at 6 AM and 2 PM UTC (default)
PIPELINE_RUN_HOURS=6,14

# Run every 6 hours
PIPELINE_RUN_HOURS=0,6,12,18

# Run once a day at noon
PIPELINE_RUN_HOURS=12
```

---

## Telegram Notifications

You receive 4 types of notifications:

| Trigger | Emoji | What You See |
|---------|-------|-------------|
| Pipeline starts | 🚀 | Run number, schedule time, GitHub Actions link |
| Pipeline succeeds | ✅ | Article title, category, YouTube link, warnings |
| Pipeline fails | ❌ | Which step failed, error message, log link |
| Scheduler starts | 🔧 | Config summary (videos/day, run hours, auto upload) |

**Setup from scratch:**
1. Message @BotFather → `/newbot` → copy token
2. Message your bot → send "Hi"
3. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find `"chat":{"id": YOUR_NUMBER}` — that's your chat ID
5. Add both to `.env`

**Common mistake:** The bot's ID (from the token, e.g., `123456789`) is NOT your chat ID. Your chat ID is always a different, larger number.

---

## YouTube Upload Details

### Upload Flow

1. **Sanitization:** Strips HTML, special characters from titles/descriptions
2. **Tag Management:** Auto-adds "shorts" tag, enforces 30-tag limit, 30-char per tag
3. **Thumbnail:** Auto-uploads custom AI-generated thumbnail
4. **Privacy:** Defaults to public
5. **Safety:** Skips upload if `REVIEW_BEFORE_UPLOAD=true` and `AUTO_UPLOAD=false`

### Auth Strategies (Local vs CI)

The uploader supports two authentication methods:

| Environment | Auth Method | Token Storage |
|-------------|------------|---------------|
| **Local** | `config/youtube_token.json` | File on disk |
| **GitHub Actions** | Environment variables | `YOUTUBE_REFRESH_TOKEN` + `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET` |

In CI, the uploader auto-refreshes expired tokens and saves them locally for the session.

### If Upload Fails

- Videos are always saved locally in `output/videos/` regardless of upload status
- Check `pipeline.log` for error details
- Re-authenticate: `python scripts/auth_youtube.py`
- Check Google Cloud Console for API quota

---

## Database Schema

15 tables tracking everything:

| Table | Records | Purpose |
|-------|---------|---------|
| `sources` | 76+ | RSS/API news source definitions |
| `articles` | Growing | All fetched articles with FTS5 search |
| `used_articles` | Growing | Articles already turned into videos (no duplicates) |
| `article_embeddings` | Growing | Vector embeddings for similarity |
| `trends` | Growing | Detected trending topics |
| `scripts` | Growing | Generated video scripts |
| `thumbnails` | Growing | Generated thumbnails |
| `seo_metadata` | Growing | SEO-optimized titles/descriptions/tags |
| `audio_files` | Growing | TTS narration files |
| `videos` | Growing | Assembled video files |
| `uploads` | Growing | YouTube upload records |
| `analytics` | Growing | Video performance metrics |
| `learning_insights` | Growing | Self-improvement data |
| `pipeline_runs` | Growing | Every pipeline execution record |
| `agent_memory` | Growing | Short/long/episodic agent memory |

**Query recent runs:**
```python
import sqlite3
conn = sqlite3.connect('news_pipeline.db')
for row in conn.execute('SELECT id, status, videos_produced, started_at FROM pipeline_runs ORDER BY id DESC LIMIT 5'):
    print(row)
```

---

## Troubleshooting

### "No YouTube credentials found" / Uploads skipped
```bash
# Re-run OAuth flow
python scripts/auth_youtube.py

# Verify token exists
type config\youtube_token.json
```

### Telegram not receiving messages
```bash
# Test the connection
python -c "
import httpx, os
from dotenv import load_dotenv
load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')
print(f'Token: {token[:10]}...' if token else 'NO TOKEN')
print(f'Chat ID: {chat_id}')
r = httpx.post(f'https://api.telegram.org/bot{token}/sendMessage', json={'chat_id': chat_id, 'text': 'Test'}, timeout=10)
print(f'Status: {r.status_code}')
"
```

### Pipeline produces 0 videos
```bash
# Check health
python scripts/run_pipeline.py --health

# Check FFmpeg
ffmpeg -version

# Check logs
type pipeline.log | findstr ERROR
```

### Pipeline produces 1 video instead of 2
- Check `VIDEOS_PER_DAY=2` in `.env`
- Check `PIPELINE_RUN_HOURS=6,14` (must have 2 hours)
- If using GitHub Actions: verify secrets are set with `gh secret list`
- Check workflow runs: `gh run list --repo $REPO`

### GitHub Actions fails
```bash
# Check secrets
gh secret list --repo YOUR_USERNAME/ai-news-youtube

# View failed run logs
gh run view <run-id> --log-failed --repo YOUR_USERNAME/ai-news-youtube
```

### FFmpeg not found
```bash
# Windows
winget install Gyan.FFmpeg

# Mac
brew install ffmpeg

# Linux
sudo apt install ffmpeg
```

### "hatch build" error in CI
The `pyproject.toml` includes `[tool.hatch.build.targets.wheel]` config. If you see build errors, ensure the packages list matches your directories.

---

## File Structure

```
ai-news-youtube/
├── agents/                        # 13 LangGraph agents
│   ├── collector.py               # Fetches from 76+ RSS feeds
│   ├── trend_detector.py          # Trending topic detection
│   ├── verifier.py                # Fact-checking + content moderation
│   ├── ranker.py                  # Article ranking for Shorts
│   ├── seo.py                     # SEO metadata generation
│   ├── scriptwriter.py            # Video script writing
│   ├── reviewer.py                # Quality review loop
│   ├── thumbnail.py               # AI thumbnail generation
│   ├── narrator.py                # TTS with word-level captions
│   ├── video.py                   # FFmpeg video assembly
│   ├── uploader.py                # YouTube upload orchestration
│   ├── analytics.py               # Run recording
│   ├── learner.py                 # Self-improvement loop
│   ├── notifier.py                # Telegram notifications
│   ├── state.py                   # Pipeline state type
│   └── tools/
│       ├── llm_router.py          # Multi-provider LLM routing
│       ├── youtube_api.py         # YouTube OAuth + upload
│       ├── web_search.py          # Web search
│       ├── rss_parser.py          # RSS feed parsing
│       ├── image_gen.py           # Image generation
│       ├── moderation.py          # Content safety
│       └── scripts.py             # Script utilities
├── workflows/
│   └── pipeline.py                # LangGraph pipeline graph
├── database/
│   ├── __init__.py                # DB initialization
│   └── schema.sql                 # 15 tables + FTS5
├── scripts/
│   ├── run_pipeline.py            # Single run entry point
│   ├── scheduler.py               # Never-stop scheduler
│   ├── seed_sources.py            # 76+ news sources
│   ├── auth_youtube.py            # YouTube OAuth flow
│   ├── setup_telegram.py          # Interactive Telegram setup
│   ├── collect_analytics.py       # Analytics collection
│   ├── sync_turso.py              # Cloud DB sync
│   └── status.py                  # Status check
├── dashboard/                     # Next.js monitoring dashboard
├── config.py                      # Central config (loads .env)
├── health.py                      # System health checks
├── .github/workflows/
│   └── daily_news.yml             # GitHub Actions cron (2x/day)
├── pyproject.toml                 # Python package config
├── Makefile                       # Quick commands
├── .env.example                   # Environment template
├── output/                        # Generated files (auto-created)
│   ├── videos/                    # MP4 Shorts (1080x1920)
│   ├── audio/                     # MP3 narrations
│   └── thumbnails/                # JPG thumbnails
└── news_pipeline.db               # SQLite database (auto-created)
```

---

## Quick Commands Reference

```bash
# Setup
make setup                        # Create venv + install
pip install -e .                  # Same as above

# Run
python scripts/run_pipeline.py --mode daily_news    # Run once
python scripts/run_pipeline.py --mode shorts        # Shorts mode
python scripts/run_pipeline.py --mode deep_dive     # Deep dive mode

# Scheduler
python scripts/scheduler.py       # Start never-stop scheduler
python scripts/scheduler.py --health     # Health check
python scripts/scheduler.py --validate   # Config validation

# Setup helpers
python scripts/auth_youtube.py    # YouTube OAuth flow
python scripts/setup_telegram.py  # Interactive Telegram setup
python scripts/seed_sources.py    # Seed 76+ news sources
python scripts/collect_analytics.py  # Collect analytics

# GitHub Actions
gh workflow run daily_news.yml --repo YOUR_USERNAME/ai-news-youtube
gh run list --repo $REPO
gh secret list --repo YOUR_USERNAME/ai-news-youtube

# Health
python scripts/run_pipeline.py --health
python scripts/run_pipeline.py --validate
```

---

## License

MIT
