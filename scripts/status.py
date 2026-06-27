"""
SYSTEM STATUS CHECK
===================
Shows current health of all components.
Run: python scripts/status.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.tools.llm_router import LLMRouter
import shutil


def check():
    print("\n" + "=" * 60)
    print("  AI NEWS PIPELINE — SYSTEM STATUS")
    print("=" * 60)

    router = LLMRouter()
    status = router.get_status()

    print("\n--- LLM Providers ---")
    for name, info in status.items():
        icon = "✓" if info["available"] else "✗"
        cooldown = f" (cooldown {info['cooldown_remaining']}s)" if info["cooldown_remaining"] > 0 else ""
        error = f" [{info['last_error']}]" if info["last_error"] else ""
        print(f"  {icon} {name:15s} | requests: {info['requests_today']:5d} | tokens: {info['tokens_today']:8d}{cooldown}{error}")

    print("\n--- Local Tools ---")
    for tool, cmd in [("ffmpeg", "ffmpeg -version"), ("ollama", "ollama --version"), ("python", "python --version")]:
        path = shutil.which(tool)
        icon = "✓" if path else "✗"
        print(f"  {icon} {tool:15s} | {'found at ' + path if path else 'NOT FOUND'}")

    print("\n--- Database ---")
    import sqlite3
    db_path = "news_pipeline.db"
    if Path(db_path).exists():
        conn = sqlite3.connect(db_path)
        runs = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        uploads = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
        articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] if "articles" in [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()] else 0
        conn.close()
        print(f"  ✓ {db_path} | runs: {runs} | uploads: {uploads} | articles: {articles}")
    else:
        print(f"  ✗ {db_path} | NOT FOUND (run: python scripts/seed_sources.py)")

    print("\n--- API Keys ---")
    import os
    keys = {
        "GROQ_API_KEY": "Groq (LLM)",
        "OPENROUTER_API_KEY": "OpenRouter (fallback LLM)",
        "YOUTUBE_API_KEY": "YouTube (upload)",
        "TOGETHER_API_KEY": "Together AI (images)",
    }
    for env_key, name in keys.items():
        val = os.getenv(env_key, "")
        icon = "✓" if val and val != "gsk_xxxxx" and not val.startswith("xxxxx") else "✗"
        print(f"  {icon} {name:25s} | {'SET' if icon == '✓' else 'NOT SET'}")

    print("\n" + "=" * 60)
    print("  Run 'python scripts/scheduler.py' to start the never-stop pipeline")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    check()
