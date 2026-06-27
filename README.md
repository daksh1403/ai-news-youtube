# AI News YouTube — Autonomous Multi-Agent Pipeline

**Zero-cost, never-stop AI news channel** that discovers, verifies, ranks, scripts, voices, and uploads **2 videos daily** to YouTube — fully autonomous via GitHub Actions.

## How It Works

```
News Sources (76+ RSS/APIs) → Collector → Trend Detector → Verifier → Ranker
    → SEO Optimizer → Script Writer ↔ Reviewer (loop)
    → Thumbnail Generator → Narrator (TTS) → Video Assembler
    → YouTube Upload → Analytics Collector → Learning Loop
```

**13 LangGraph agents** working in sequence with fact verification, quality review loops, and self-improvement.

## Tech Stack

| Component | Tool | Cost |
|-----------|------|------|
| Orchestration | LangGraph | Free |
| LLM | Groq (Llama 3.1 8B / 3.3 70B) | Free |
| Embeddings | Ollama (nomic-embed-text) | Free |
| TTS | edge-tts / Piper TTS | Free |
| Video | FFmpeg | Free |
| Thumbnails | Pollinations.ai | Free |
| Upload | YouTube Data API v3 | Free |
| Database | SQLite | Free |
| Scheduling | GitHub Actions (cron) + Local Scheduler | Free |
| Notifications | Telegram Bot API | Free |

**Total cost: $0/month**

## Quick Start

```bash
# Clone
git clone https://github.com/daksh1403/ai-news-youtube.git
cd ai-news-youtube

# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys (see "Configuration" below)

# Initialize DB
python scripts/seed_sources.py

# Run once
python scripts/run_pipeline.py --mode daily_news

# Start never-stop scheduler (2 videos/day)
python scripts/scheduler.py
```

Or use Make:
```bash
make setup      # create venv + install
make run        # run pipeline once
make schedule   # start never-stop scheduler
make seed       # seed news sources
make analytics  # collect analytics
```

## Configuration

### `.env` File

Copy `.env.example` to `.env` and fill in:

```env
# === Required ===
GROQ_API_KEY=gsk_xxxxx

# === YouTube Upload (OAuth) ===
YOUTUBE_CLIENT_ID=xxxxx.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-xxxxx
YOUTUBE_REFRESH_TOKEN=1//xxxxx

# === Telegram Notifications ===
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=6786429335

# === Pipeline Settings ===
VIDEOS_PER_DAY=2
PIPELINE_RUN_HOURS=6,14
AUTO_UPLOAD=true
REVIEW_BEFORE_UPLOAD=false
CONTENT_MODERATION_STRICT=true
MAX_ARTICLES_PER_RUN=50

# === Optional ===
OPENROUTER_API_KEY=
TOGETHER_API_KEY=
TURSO_DATABASE_URL=
TURSO_AUTH_TOKEN=
DISCORD_WEBHOOK_URL=
TTS_ENGINE=edge-tts
TTS_VOICE=en-US-ChristopherNeural
IMAGE_PROVIDER=pollinations
```

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq API for LLM inference (free at console.groq.com) |
| `YOUTUBE_CLIENT_ID` | ✅ | — | Google Cloud OAuth client ID |
| `YOUTUBE_CLIENT_SECRET` | ✅ | — | Google Cloud OAuth client secret |
| `YOUTUBE_REFRESH_TOKEN` | ✅ | — | OAuth refresh token for YouTube upload |
| `TELEGRAM_BOT_TOKEN` | Recommended | — | Telegram bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Recommended | — | Your personal Telegram chat ID |
| `VIDEOS_PER_DAY` | — | `2` | Number of videos to produce daily (1-10) |
| `PIPELINE_RUN_HOURS` | — | `6,14` | Comma-separated hours (UTC) to run pipeline |
| `AUTO_UPLOAD` | — | `false` | Auto-upload to YouTube without review |
| `REVIEW_BEFORE_UPLOAD` | — | `true` | Pause upload for manual review |
| `CONTENT_MODERATION_STRICT` | — | `true` | Strict content safety filtering |
| `MAX_ARTICLES_PER_RUN` | — | `50` | Max articles to fetch per pipeline run |
| `OPENROUTER_API_KEY` | — | — | Fallback LLM provider |
| `TTS_ENGINE` | — | `edge-tts` | TTS engine (`edge-tts` or `piper`) |
| `TTS_VOICE` | — | `en-US-ChristopherNeural` | Voice for narration |
| `IMAGE_PROVIDER` | — | `pollinations` | Thumbnail generation service |
| `DATABASE_PATH` | — | `news_pipeline.db` | SQLite database file path |

## Scheduling — 2 Videos/Day

### Option 1: GitHub Actions (Recommended)

The pipeline runs automatically via GitHub Actions cron at **06:00 UTC** and **14:00 UTC** every day. This is the most reliable option — it runs even if your computer is off.

**Required GitHub Secrets** (Settings → Secrets → Actions):

| Secret | How to Get |
|--------|------------|
| `GROQ_API_KEY` | Copy from console.groq.com |
| `YOUTUBE_CLIENT_ID` | Copy from Google Cloud Console |
| `YOUTUBE_CLIENT_SECRET` | Copy from Google Cloud Console |
| `YOUTUBE_REFRESH_TOKEN` | From `config/youtube_token.json` → `refresh_token` field |
| `TELEGRAM_BOT_TOKEN` | From @BotFather |
| `TELEGRAM_CHAT_ID` | Your personal chat ID |

Set all secrets:
```bash
gh secret set GROQ_API_KEY --body "gsk_xxxxx" --repo daksh1403/ai-news-youtube
gh secret set YOUTUBE_CLIENT_ID --body "xxxxx.apps.googleusercontent.com" --repo daksh1403/ai-news-youtube
gh secret set YOUTUBE_CLIENT_SECRET --body "GOCSPX-xxxxx" --repo daksh1403/ai-news-youtube
gh secret set YOUTUBE_REFRESH_TOKEN --body "1//xxxxx" --repo daksh1403/ai-news-youtube
gh secret set TELEGRAM_BOT_TOKEN --body "123456789:ABCdef..." --repo daksh1403/ai-news-youtube
gh secret set TELEGRAM_CHAT_ID --body "6786429335" --repo daksh1403/ai-news-youtube
```

**Manual trigger:**
```bash
gh workflow run daily_news.yml --repo daksh1403/ai-news-youtube
```

### Option 2: Local Scheduler

Runs continuously on your machine. Keeps 2 videos/day schedule:

```bash
python scripts/scheduler.py
```

- Runs at configured hours (default: 06:00 and 14:00)
- If a run fails, the next run still happens
- 2-minute retry on pipeline failures, 5-minute wait on critical errors
- Daily API limit reset at midnight
- Press Ctrl+C to stop gracefully

**Scheduler commands:**
```bash
python scripts/scheduler.py --health     # Run health check
python scripts/scheduler.py --validate   # Validate config only
```

## Project Structure

```
ai-news-youtube/
├── agents/                    # 13 LangGraph agents
│   ├── collector.py           # Fetches articles from 76+ RSS/API sources
│   ├── trend_detector.py      # Identifies trending topics via embeddings
│   ├── verifier.py            # Fact-checks articles using LLM
│   ├── ranker.py              # Ranks articles by relevance + quality
│   ├── seo.py                 # SEO optimization for titles/descriptions
│   ├── scriptwriter.py        # Generates YouTube video scripts
│   ├── reviewer.py            # Quality review loop (auto-reject/approve)
│   ├── thumbnail.py           # Generates thumbnails via Pollinations.ai
│   ├── narrator.py            # TTS narration (edge-tts / Piper)
│   ├── video.py               # FFmpeg video assembly
│   ├── uploader.py            # YouTube upload via Data API v3
│   ├── analytics.py           # Collects video performance metrics
│   ├── learner.py             # Self-improvement learning loop
│   ├── notifier.py            # Telegram notification system
│   ├── state.py               # Pipeline state management
│   └── tools/
│       ├── llm_router.py      # Multi-provider LLM routing (Groq→OpenRouter→Ollama)
│       ├── youtube_api.py     # YouTube OAuth + upload (env-based auth for CI)
│       ├── web_search.py      # Web search for article gathering
│       ├── rss_parser.py      # RSS feed parsing
│       ├── image_gen.py       # Image generation
│       ├── moderation.py      # Content safety / moderation
│       └── scripts.py         # Script utilities
├── workflows/
│   └── pipeline.py            # LangGraph pipeline graph definition
├── database/
│   ├── __init__.py            # DB initialization
│   └── schema.sql             # 15 tables with FTS5 search
├── scripts/
│   ├── run_pipeline.py        # Single pipeline run entry point
│   ├── scheduler.py           # Never-stop 2x/day scheduler
│   ├── seed_sources.py        # Initialize 76+ news sources
│   ├── auth_youtube.py        # YouTube OAuth flow helper
│   ├── setup_telegram.py      # Interactive Telegram bot setup
│   ├── collect_analytics.py   # Analytics collection script
│   ├── sync_turso.py          # Sync to Turso cloud DB
│   └── status.py              # Status check script
├── dashboard/                 # Next.js monitoring dashboard
│   ├── app/                   # App router pages
│   └── lib/db.ts              # Turso DB client
├── config.py                  # Central configuration (loads .env)
├── health.py                  # System health checks (FFmpeg, Ollama, DB)
├── .github/workflows/
│   └── daily_news.yml         # GitHub Actions: 2 videos/day cron
├── pyproject.toml             # Python package config (hatchling)
├── Makefile                   # Quick commands
├── .env.example               # Environment template
└── news_pipeline.db           # SQLite database (auto-created)
```

## Telegram Notifications

The pipeline sends rich HTML notifications to Telegram for:

| Event | Message |
|-------|---------|
| ✅ Pipeline success | Article title, category, YouTube link, warnings |
| ❌ Pipeline failure | Which step failed, error details, log link |
| 🚀 Scheduler startup | Config summary (videos/day, run hours) |
| 📊 Daily summary | Runs, uploads, errors count |

### Setup Telegram

**Method 1 — Interactive script:**
```bash
python scripts/setup_telegram.py
```

**Method 2 — Manual:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot`
2. Copy the bot token
3. Message your new bot (send "Hi")
4. Get your chat ID: visit `https://api.telegram.org/bot<TOKEN>/getUpdates` — look for `"chat":{"id": NUMBER}`
5. Add to `.env`:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   TELEGRAM_CHAT_ID=your_chat_id_here
   ```

**Important:** The chat ID from `getUpdates` is your personal ID (e.g., `6786429335`), NOT the bot's own ID from the token. The bot's token `123456789:ABC...` starts with the bot's ID, but your chat ID is different.

## YouTube Upload

### Setup OAuth

1. Create a project in [Google Cloud Console](https://console.cloud.google.com)
2. Enable **YouTube Data API v3**
3. Create **OAuth 2.0 credentials** (Desktop app)
4. Download `client_secrets.json` → place in `config/client_secrets.json`
5. Run the auth flow:
   ```bash
   python scripts/auth_youtube.py
   ```
6. This saves `config/youtube_token.json` with your refresh token

### Upload Flow

The uploader (`agents/uploader.py`) handles:
- **Sanitization**: Strips HTML/special characters from titles, descriptions, tags
- **Tag management**: Auto-adds "shorts" tag, enforces limits (30 tags, 30 chars each)
- **Thumbnail**: Auto-uploads custom thumbnail if available
- **Privacy**: Defaults to public upload
- **Safety**: Skips upload if `REVIEW_BEFORE_UPLOAD=true` and `AUTO_UPLOAD=false`

### Auth Strategies (CI/CD)

The YouTube uploader (`agents/tools/youtube_api.py`) supports two auth strategies:

1. **Local file** (`config/youtube_token.json`) — for local development
2. **Environment variables** — for GitHub Actions CI:
   - `YOUTUBE_REFRESH_TOKEN`
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`

In CI, the uploader auto-refreshes the token and saves it locally for subsequent requests.

## Database Schema (15 Tables)

| Table | Purpose |
|-------|---------|
| `sources` | 76+ RSS/API news sources |
| `articles` | Fetched articles with FTS5 full-text search |
| `used_articles` | Track which articles have been used (no duplicates) |
| `article_embeddings` | Vector embeddings for similarity search |
| `trends` | Detected trending topics with scores |
| `scripts` | Generated video scripts with quality scores |
| `thumbnails` | Generated thumbnails with prompts |
| `seo_metadata` | Optimized titles, descriptions, tags |
| `audio_files` | TTS narration files |
| `videos` | Assembled video files |
| `uploads` | YouTube upload records + status |
| `analytics` | Video performance metrics |
| `learning_insights` | Self-improvement insights |
| `pipeline_runs` | Every pipeline execution record |
| `agent_memory` | Short/long/episodic agent memory |

## Health Check

```bash
python scripts/run_pipeline.py --health
python scripts/scheduler.py --health
```

Checks: Python version, FFmpeg, Ollama, database integrity, output directory stats.

## Pipeline Modes

```bash
python scripts/run_pipeline.py --mode daily_news    # Standard daily news (default)
python scripts/run_pipeline.py --mode shorts        # YouTube Shorts format
python scripts/run_pipeline.py --mode deep_dive     # In-depth analysis
python scripts/run_pipeline.py --health             # Health check
python scripts/run_pipeline.py --validate           # Config validation only
```

## Content Safety

- **Strict moderation** by default (`CONTENT_MODERATION_STRICT=true`)
- Articles are fact-checked by LLM before processing
- Quality review loop: scripts auto-reviewed, rejected scripts are regenerated
- Content filtered for violence, hate speech, misinformation
- Optional human review gate (`REQUIRE_HUMAN_REVIEW=true`)

## Dashboard

A Next.js monitoring dashboard is included in `dashboard/`:
```bash
cd dashboard
npm install
npm run dev
```
Connects to Turso cloud DB for real-time pipeline monitoring.

## API Keys Needed

1. **Groq** (free): https://console.groq.com — LLM inference
2. **YouTube Data API** (free): Google Cloud Console — video upload
3. **Telegram Bot** (free): @BotFather on Telegram — notifications
4. **Optional**: OpenRouter, Together AI (fallback LLM/image gen)

## Troubleshooting

### Telegram not receiving messages
- Check `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
- Verify chat ID is YOUR ID (from `getUpdates`), not the bot's ID from the token
- Send a message to your bot first, then check `getUpdates`

### YouTube upload fails
- Verify `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` are set
- Re-run `python scripts/auth_youtube.py` if token expired
- Check Google Cloud Console for API quota

### Pipeline produces only 1 video instead of 2
- Check `VIDEOS_PER_DAY=2` in `.env`
- Ensure GitHub Actions secrets are all set (missing secrets = skipped steps)
- Check workflow runs: `gh run list --repo daksh1403/ai-news-youtube`

### GitHub Actions workflow fails
- Check secrets are set: `gh secret list --repo daksh1403/ai-news-youtube`
- View logs: `gh run view <run-id> --log-failed --repo daksh1403/ai-news-youtube`
- Ensure `pip install -e .` works (hatch build config is set up)

### FFmpeg not found
- Install: `winget install Gyan.FFmpeg` (Windows) or `apt install ffmpeg` (Linux)
- Or install via: `choco install ffmpeg`

## License

MIT
