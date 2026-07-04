"""
NEVER-STOP SCHEDULER v5
========================
With config validation, health checks, YouTube safety guardrails,
and lifetime reliability features (log rotation, disk cleanup, watchdog).

Fallback chain: Groq → OpenRouter → Cerebras → Ollama (local, always works)
The scheduler NEVER stops, even when API keys run out.

Usage:
    python scripts/scheduler.py
    python scripts/scheduler.py --health
    python scripts/scheduler.py --validate
"""

import sys
import os
import asyncio
import signal
import logging
import time
import traceback
import shutil
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from workflows.pipeline import run_pipeline
from agents.tools.llm_router import LLMRouter
from agents.notifier import get_notifier
from config import load_config, print_config_report
from health import run_health_check, print_health_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("pipeline.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

running = True


def handle_signal(sig, frame):
    global running
    logger.info(f"Received signal {sig}, shutting down gracefully...")
    running = False


if sys.platform != "win32":
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
else:
    signal.signal(signal.SIGINT, handle_signal)


# ── LIFETIME RELIABILITY: Log rotation ─────────────────────────────
def rotate_logs(max_size_mb: int = 50, keep_backups: int = 3):
    """Rotate log files when they exceed max_size_mb."""
    for log_file in ["pipeline.log", "scheduler_error.log"]:
        log_path = Path(log_file)
        if log_path.exists():
            size_mb = log_path.stat().st_size / (1024 * 1024)
            if size_mb > max_size_mb:
                logger.info(f"Rotating {log_file} ({size_mb:.1f}MB > {max_size_mb}MB)")
                # Remove oldest backup
                oldest = Path(f"{log_file}.{keep_backups}")
                if oldest.exists():
                    oldest.unlink()
                # Shift backups
                for i in range(keep_backups - 1, 0, -1):
                    src = Path(f"{log_file}.{i}")
                    dst = Path(f"{log_file}.{i + 1}")
                    if src.exists():
                        src.rename(dst)
                # Current becomes .1
                log_path.rename(f"{log_file}.1")
                # Create new empty log
                Path(log_file).touch()


# ── LIFETIME RELIABILITY: Disk cleanup ─────────────────────────────
def cleanup_old_files(output_dir: str = "output", max_days: int = 30, max_files: int = 200):
    """Remove old output files to prevent disk space exhaustion."""
    output = Path(output_dir)
    if not output.exists():
        return

    cutoff = datetime.now() - timedelta(days=max_days)
    removed = 0

    for subdir in ["videos", "audio", "thumbnails"]:
        dir_path = output / subdir
        if not dir_path.exists():
            continue

        files = sorted(dir_path.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)

        # Remove files older than max_days
        for f in files:
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    f.unlink()
                    removed += 1
            except Exception:
                pass

        # Also enforce max file count (keep newest)
        files = sorted(dir_path.glob("*"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in files[max_files:]:
            try:
                f.unlink()
                removed += 1
            except Exception:
                pass

    if removed > 0:
        logger.info(f"Cleaned up {removed} old output files")


# ── LIFETIME RELIABILITY: Database maintenance ─────────────────────
def maintain_database(db_path: str, max_runs: int = 500):
    """Keep database size in check by pruning old records."""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path, timeout=5)

        # Count pipeline runs
        count = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
        if count > max_runs:
            # Keep only the most recent runs
            delete_count = count - max_runs
            conn.execute(
                "DELETE FROM pipeline_runs WHERE id NOT IN "
                "(SELECT id FROM pipeline_runs ORDER BY id DESC LIMIT ?)",
                (max_runs,),
            )
            conn.commit()
            logger.info(f"Pruned {delete_count} old pipeline runs from database")

        conn.close()
    except Exception as e:
        logger.debug(f"Database maintenance skipped: {e}")


# ── LIFETIME RELIABILITY: Health watchdog ───────────────────────────
def check_system_health():
    """Quick health checks to catch issues before they become critical."""
    warnings = []

    # Check disk space (warn if < 1GB free)
    try:
        stat = shutil.disk_usage(".")
        free_gb = stat.free / (1024 ** 3)
        if free_gb < 1:
            warnings.append(f"LOW DISK SPACE: {free_gb:.1f}GB remaining")
    except Exception:
        pass

    # Check if FFmpeg is still available
    if not shutil.which("ffmpeg"):
        warnings.append("FFmpeg not found in PATH")

    # Check database integrity
    db_path = "news_pipeline.db"
    if Path(db_path).exists():
        try:
            import sqlite3
            conn = sqlite3.connect(db_path, timeout=5)
            conn.execute("SELECT COUNT(*) FROM pipeline_runs")
            conn.close()
        except Exception:
            warnings.append("Database corruption detected")

    for w in warnings:
        logger.warning(f"HEALTH CHECK: {w}")

    return warnings


def reset_daily_limits():
    router = LLMRouter()
    router.reset_daily()
    logger.info("Daily API limits reset")


async def execute_pipeline_with_retry(config, mode: str = "daily_news", max_retries: int = 2):
    for attempt in range(max_retries + 1):
        start = datetime.now()
        logger.info(f"PIPELINE RUN — {start.strftime('%Y-%m-%d %H:%M:%S')} | Attempt: {attempt + 1}/{max_retries + 1}")

        try:
            result = await run_pipeline(mode=mode, config=config)
            elapsed = (datetime.now() - start).total_seconds()

            if result.get("error"):
                logger.error(f"Run error after {elapsed:.0f}s: {result['error']}")
            else:
                logger.info(f"Run SUCCESS in {elapsed:.0f}s")
                logger.info(f"  Video: {result.get('video_path', 'N/A')}")
                logger.info(f"  YouTube: {result.get('youtube_url', 'N/A')}")
                logger.info(f"  Blocked: {result.get('blocked_count', 0)} | Flagged: {result.get('flagged_count', 0)}")
                return result

        except Exception as e:
            elapsed = (datetime.now() - start).total_seconds()
            logger.error(f"Run FAILED after {elapsed:.0f}s: {e}")
            traceback.print_exc()

        if attempt < max_retries:
            wait = 120
            logger.info(f"Retrying in {wait}s...")
            elapsed_wait = 0
            while running and elapsed_wait < wait:
                await asyncio.sleep(min(10, wait - elapsed_wait))
                elapsed_wait += 10

    logger.warning("All retries exhausted, continuing to next scheduled time")
    return {"error": "all_retries_failed"}


def get_next_run_time(hour: int) -> datetime:
    now = datetime.now()
    target = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return target


def calculate_sleep_seconds(next_run: datetime) -> float:
    delta = (next_run - datetime.now()).total_seconds()
    return max(0, delta)


async def scheduler_loop():
    global running

    config = load_config()
    print_config_report(config)

    router = LLMRouter()
    status = router.get_status()
    available = [p for p, s in status.items() if s.get("available")]

    notifier = get_notifier()

    logger.info(f"AI NEWS PIPELINE — NEVER-STOP SCHEDULER v4")
    logger.info(f"Videos per day: {config.videos_per_day}")
    logger.info(f"Run hours: {', '.join(f'{h:02d}:00' for h in config.pipeline_run_hours)}")
    logger.info(f"Database: {config.database_path}")
    logger.info(f"LLM Providers: {', '.join(available)}")
    logger.info(f"Fallback chain: Groq→OpenRouter→Cerebras→Ollama→Template")
    logger.info(f"Auto upload: {config.auto_upload}")
    logger.info(f"Content moderation: {'strict' if config.content_moderation_strict else 'standard'}")
    logger.info(f"Telegram: {'enabled' if notifier.enabled else 'disabled'}")
    logger.info(f"Press Ctrl+C to stop")

    notifier.send_scheduler_startup(config)

    init_db(config.database_path)
    reset_daily_limits()

    run_count = 0
    last_reset_day = datetime.now().day
    last_maintenance_day = datetime.now().day

    while running:
        current_day = datetime.now().day
        if current_day != last_reset_day:
            reset_daily_limits()
            last_reset_day = current_day

        # Daily maintenance (once per day)
        if current_day != last_maintenance_day:
            try:
                rotate_logs()
                cleanup_old_files()
                maintain_database(config.database_path)
                check_system_health()
                last_maintenance_day = current_day
            except Exception as e:
                logger.error(f"Maintenance error: {e}")

        now = datetime.now()
        next_runs = sorted(get_next_run_time(h) for h in config.pipeline_run_hours)
        next_run = next_runs[0]
        for nr in next_runs:
            if nr > now:
                next_run = nr
                break

        sleep_sec = calculate_sleep_seconds(next_run)
        hours = int(sleep_sec // 3600)
        minutes = int((sleep_sec % 3600) // 60)

        logger.info(f"Next run at {next_run.strftime('%H:%M')} ({hours}h {minutes}m)")
        logger.info(f"Sleeping... (Ctrl+C to stop)")

        sleep_interval = 30
        elapsed = 0
        while running and elapsed < sleep_sec:
            chunk = min(sleep_interval, sleep_sec - elapsed)
            await asyncio.sleep(chunk)
            elapsed += chunk

            # Poll for Telegram bot commands during sleep
            if notifier.enabled:
                try:
                    notifier.check_commands(config.database_path)
                except Exception:
                    pass

        if not running:
            break

        run_count += 1
        logger.info(f"====== RUN #{run_count} STARTING ======")

        # Notify of starting run
        try:
            notifier.send_run_starting(run_id=f"#{run_count}")
        except Exception:
            pass

        try:
            result = await execute_pipeline_with_retry(config, mode="daily_news", max_retries=2)
            if result.get("error"):
                notifier.send_run_failure(
                    run_id=result.get("run_id", f"#{run_count}"),
                    error=result["error"],
                    failed_step=result.get("current_step", "unknown"),
                )
            else:
                notifier.send_run_success(result, run_id=f"#{run_count}")
        except Exception as e:
            logger.critical(f"CRITICAL ERROR (should never happen): {e}")
            traceback.print_exc()
            notifier.send_run_failure(
                run_id=f"#{run_count}",
                error=str(e),
                failed_step="scheduler",
            )
            logger.info("Waiting 5 minutes...")
            retry_wait = 300
            retry_elapsed = 0
            while running and retry_elapsed < retry_wait:
                await asyncio.sleep(min(30, retry_wait - retry_elapsed))
                retry_elapsed += 30

        logger.info(f"====== RUN #{run_count} FINISHED ======")
        logger.info(f"Total runs: {run_count}")

        provider_status = router.get_status()
        for name, info in provider_status.items():
            logger.info(f"  {name}: requests={info['requests_today']} cooldown={info['cooldown_remaining']}s")

    logger.info("Shutdown complete")


if __name__ == "__main__":
    if "--health" in sys.argv:
        print_health_report()
        sys.exit(0)
    if "--validate" in sys.argv:
        config = load_config()
        print_config_report(config)
        sys.exit(0)

    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)
