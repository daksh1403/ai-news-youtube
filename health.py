import os
import sys
import time
import sqlite3
import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def check_ffmpeg() -> dict:
    search_paths = [
        "ffmpeg",
        str(Path.home() / "AppData/Local/Microsoft/WinGet/Packages/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe/ffmpeg-8.1.1-full_build/bin/ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        str(Path.home() / "scoop/shims/ffmpeg.exe"),
    ]
    for path in search_paths:
        try:
            result = subprocess.run([path, "-version"], capture_output=True, timeout=5)
            if result.returncode == 0:
                version_line = result.stdout.decode().split("\n")[0]
                return {"status": "ok", "path": path, "version": version_line}
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return {"status": "missing", "path": None, "version": None}


def check_ollama() -> dict:
    try:
        import httpx
        resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return {"status": "ok", "models": [m["name"] for m in models]}
        return {"status": "error", "code": resp.status_code}
    except Exception as e:
        return {"status": "missing", "error": str(e)[:100]}


def check_database(db_path: str) -> dict:
    try:
        conn = sqlite3.connect(db_path, timeout=5)
        cursor = conn.execute("SELECT COUNT(*) FROM used_articles")
        used_count = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM pipeline_runs")
        run_count = cursor.fetchone()[0]
        cursor = conn.execute("SELECT COUNT(*) FROM review_queue")
        review_count = cursor.fetchone()[0]
        conn.close()
        return {
            "status": "ok",
            "used_articles": used_count,
            "pipeline_runs": run_count,
            "review_queue": review_count,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)[:100]}


def check_output_dir() -> dict:
    output = Path("output")
    videos = list((output / "videos").glob("*.mp4")) if (output / "videos").exists() else []
    audio = list((output / "audio").glob("*.mp3")) if (output / "audio").exists() else []
    thumbs = list((output / "thumbnails").glob("*.jpg")) if (output / "thumbnails").exists() else []

    total_video_size = sum(f.stat().st_size for f in videos)
    return {
        "status": "ok",
        "videos": len(videos),
        "audio": len(audio),
        "thumbnails": len(thumbs),
        "total_video_mb": round(total_video_size / 1024 / 1024, 1),
    }


def run_health_check(db_path: str = "news_pipeline.db") -> dict:
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "python": {
            "version": sys.version.split()[0],
            "executable": sys.executable,
        },
        "ffmpeg": check_ffmpeg(),
        "ollama": check_ollama(),
        "database": check_database(db_path),
        "output": check_output_dir(),
    }

    all_ok = all(
        v.get("status") == "ok"
        for k, v in report.items()
        if isinstance(v, dict) and "status" in v
    )
    report["overall"] = "healthy" if all_ok else "degraded"

    return report


def print_health_report(db_path: str = "news_pipeline.db"):
    report = run_health_check(db_path)

    print("\n" + "=" * 60)
    print("  AI NEWS PIPELINE — HEALTH CHECK")
    print("=" * 60)

    print(f"\n  Overall: {report['overall'].upper()}")
    print(f"  Python:  {report['python']['version']}")

    ffmpeg = report["ffmpeg"]
    print(f"\n  FFmpeg:  {ffmpeg['status'].upper()}", end="")
    if ffmpeg.get("version"):
        print(f" — {ffmpeg['version'][:50]}")
    else:
        print(" — NOT FOUND")

    ollama = report["ollama"]
    print(f"  Ollama:  {ollama['status'].upper()}", end="")
    if ollama.get("models"):
        print(f" — {', '.join(ollama['models'][:3])}")
    else:
        print()

    db = report["database"]
    print(f"  Database: {db['status'].upper()}", end="")
    if db.get("used_articles") is not None:
        print(f" — {db['used_articles']} used articles, {db['pipeline_runs']} runs, {db['review_queue']} pending review")
    else:
        print()

    out = report["output"]
    print(f"  Output:  {out['status'].upper()} — {out.get('videos', 0)} videos, {out.get('total_video_mb', 0)} MB")

    print("\n" + "=" * 60)
    print()
