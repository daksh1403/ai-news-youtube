# AI News YouTube — Autonomous Multi-Agent Pipeline

**Zero-cost, never-stop AI news channel** that discovers, verifies, ranks, scripts, voices, and uploads 2 videos daily to YouTube — fully autonomous.

## Architecture

```
News Sources → Collector → Verifier → Ranker → SEO → Script Writer
    → Review → Thumbnail → TTS → Video Assembly → YouTube Upload
    → Analytics → Learning Loop
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
| Scheduling | GitHub Actions + Never-Stop Scheduler | Free |

**Total cost: $0/month**

## Quick Start

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/ai-news-youtube.git
cd ai-news-youtube

# Setup
python -m venv .venv
.venv\Scripts\activate
pip install -e .

# Configure
cp .env.example .env
# Edit .env with your API keys

# Initialize DB
python scripts/seed_sources.py

# Run once
python scripts/run_pipeline.py --mode daily_news

# Start never-stop scheduler (2 videos/day)
python scripts/scheduler.py
```

## API Keys Needed

1. **Groq** (free): https://console.groq.com — LLM inference
2. **YouTube Data API** (free): Google Cloud Console — video upload
3. **Optional**: OpenRouter, Together AI (fallback LLM/image gen)

## Never-Stop Scheduler

The scheduler runs 2 pipeline executions per day, every day, forever:
- Run 1: 06:00
- Run 2: 14:00
- If a run fails, the next run still happens
- The scheduler itself never stops
- 5-minute retry on critical failures

```bash
python scripts/scheduler.py
```

## Project Structure

```
ai-news-youtube/
├── agents/           # 13 LangGraph agents
├── workflows/        # Pipeline graph
├── rag/              # RAG pipeline
├── ingestion/        # News source connectors
├── voice/            # TTS engines
├── video/            # Video assembly
├── database/         # SQLite schema
├── scripts/          # Entry points
├── deployment/       # Docker + GitHub Actions
└── tests/            # Test suite
```

## License

MIT
