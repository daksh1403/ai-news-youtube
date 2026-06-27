"""
Telegram Notifier - Pipeline Monitoring
========================================
Sends rich formatted notifications after every pipeline run.
Shows success/failure status, which step failed, errors, and YouTube links.

Setup:
    1. Message @BotFather on Telegram -> /newbot -> get token
    2. Message your bot -> get chat ID from https://api.telegram.org/bot<TOKEN>/getUpdates
    3. Set env vars: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID
"""

import logging
import os
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# Pipeline steps in order - used to identify where failures occurred
PIPELINE_STEPS = [
    ("collector", "Collecting articles"),
    ("trend_detector", "Detecting trends"),
    ("verifier", "Verifying facts"),
    ("ranker", "Ranking articles"),
    ("seo_optimizer", "SEO optimization"),
    ("scriptwriter", "Writing script"),
    ("reviewer", "Quality review"),
    ("thumbnail", "Generating thumbnail"),
    ("narrator", "Narration"),
    ("video", "Video assembly"),
    ("uploader", "YouTube upload"),
    ("analytics", "Analytics"),
    ("learner", "Learning"),
]


class TelegramNotifier:
    """Sends pipeline status notifications via Telegram."""

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")
        self.enabled = bool(self.bot_token and self.chat_id)
        self._last_update_id: int = 0

    def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message via Telegram Bot API."""
        if not self.enabled:
            logger.debug("Telegram notifications disabled (no token/chat_id)")
            return False

        try:
            import httpx

            resp = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if resp.status_code == 200:
                logger.info("Telegram notification sent")
                return True
            else:
                logger.warning(f"Telegram API returned {resp.status_code}: {resp.text[:200]}")
                return False
        except ImportError:
            logger.warning("httpx not installed - cannot send Telegram notification")
            return False
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")
            return False

    def send_run_success(self, result: dict, run_id: str = "") -> bool:
        """Send a rich success notification after a pipeline run."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        article = result.get("selected_article", {})
        title = article.get("title", "N/A")
        category = article.get("category", "general")
        source = article.get("source", "N/A")

        youtube_url = result.get("youtube_url", "")
        video_path = result.get("video_path", "N/A")
        errors = result.get("errors", [])
        run_id = run_id or result.get("run_id", "???")

        # Count errors by step
        error_summary = ""
        if errors:
            step_errors = {}
            for err in errors:
                if isinstance(err, dict):
                    step = err.get("step", "unknown")
                    msg = err.get("message", str(err))
                else:
                    step = "general"
                    msg = str(err)
                step_errors.setdefault(step, []).append(msg)

            error_lines = []
            for step, msgs in step_errors.items():
                error_lines.append(f"  WARNING <b>{step}</b>: {msgs[0][:80]}")
            error_summary = "\n".join(error_lines)

        # Build message
        lines = [
            "SUCCESS <b>PIPELINE RUN COMPLETE</b>",
            f"Time: {now}",
            f"Run: <code>{run_id}</code>",
            "",
            "<b>Article:</b>",
            f"  {title[:100]}",
            f"  Category: {category} | Source: {source}",
            "",
        ]

        if youtube_url:
            lines.append(f"<b>YouTube:</b> <a href=\"{youtube_url}\">Watch Video</a>")
        else:
            lines.append(f"<b>Video:</b> saved locally ({video_path})")

        if error_summary:
            lines.extend(["", f"<b>Warnings ({len(errors)}):</b>", error_summary])

        status_emoji = "OK" if not errors else f"WARN ({len(errors)} warning(s))"
        lines.extend([
            "",
            f"Status: {status_emoji}",
        ])

        return self._send("\n".join(lines))

    def send_run_failure(
        self,
        run_id: str,
        error: str,
        failed_step: str = "",
        elapsed_seconds: float = 0,
    ) -> bool:
        """Send a failure notification with details about what went wrong."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        # Find the step label
        step_label = "Unknown step"
        if failed_step:
            for key, label in PIPELINE_STEPS:
                if key == failed_step:
                    step_label = label
                    break

        elapsed_str = ""
        if elapsed_seconds > 0:
            m, s = divmod(int(elapsed_seconds), 60)
            elapsed_str = f"Elapsed: {m}m {s}s"

        # Truncate error message for Telegram (4096 char limit)
        error_short = error[:500] if error else "Unknown error"

        lines = [
            "FAILED <b>PIPELINE RUN FAILED</b>",
            f"Time: {now}",
            f"Run: <code>{run_id}</code>",
            "",
            f"<b>Failed at:</b> {step_label}",
            "",
            "<b>Error:</b>",
            f"<pre>{error_short}</pre>",
            "",
            elapsed_str,
            "",
            "<i>Check logs: cat pipeline.log | tail -50</i>",
        ]

        return self._send("\n".join(lines))

    def send_scheduler_startup(self, config) -> bool:
        """Send a notification when the scheduler starts."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        hours = ", ".join(f"{h:02d}:00" for h in config.pipeline_run_hours)

        lines = [
            "<b>SCHEDULER STARTED</b>",
            f"Time: {now}",
            f"Videos/day: {config.videos_per_day}",
            f"Run hours: {hours}",
            f"Auto upload: {'Yes' if config.auto_upload else 'No'}",
            f"Moderation: {'Strict' if config.content_moderation_strict else 'Standard'}",
        ]

        return self._send("\n".join(lines))

    def send_daily_summary(self, runs_today: int, uploads_today: int, errors_today: int) -> bool:
        """Send end-of-day summary."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        status = "OK" if errors_today == 0 else f"WARN ({errors_today})" if errors_today < 3 else "ALERT"

        lines = [
            f"<b>DAILY SUMMARY - {now}</b>",
            "",
            f"Runs today: {runs_today}",
            f"Uploads: {uploads_today}",
            f"Errors: {errors_today}",
            f"Status: {status}",
        ]

        return self._send("\n".join(lines))

    # ── Bot Command Handlers ──────────────────────────────────────

    def check_commands(self, db_path: str = "news_pipeline.db") -> bool:
        """Poll Telegram for new messages and handle bot commands.

        Supported commands:
            /status  — Pipeline overview (last run, uploads, health)
            /runs    — Last 5 pipeline runs
            /uploads — Last 5 YouTube uploads
            /health  — System health (FFmpeg, DB, API keys)
            /help    — List of commands
        """
        if not self.enabled:
            return False

        try:
            import httpx

            params = {"timeout": 1}
            if self._last_update_id:
                params["offset"] = self._last_update_id + 1

            resp = httpx.get(
                f"https://api.telegram.org/bot{self.bot_token}/getUpdates",
                params=params,
                timeout=10,
            )
            if resp.status_code != 200:
                return False

            updates = resp.json().get("result", [])
            for update in updates:
                update_id = update.get("update_id", 0)
                if update_id > self._last_update_id:
                    self._last_update_id = update_id

                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = msg.get("text", "").strip().lower()

                # Only respond to our authorized chat
                if chat_id != self.chat_id:
                    continue

                if text == "/status":
                    self._handle_status(db_path)
                elif text == "/runs":
                    self._handle_runs(db_path)
                elif text == "/uploads":
                    self._handle_uploads(db_path)
                elif text == "/health":
                    self._handle_health(db_path)
                elif text in ("/help", "/start", "help"):
                    self._handle_help()

            return True

        except Exception as e:
            logger.warning(f"Command check failed: {e}")
            return False

    def _handle_status(self, db_path: str):
        """Handle /status command — show pipeline overview."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        try:
            conn = sqlite3.connect(db_path, timeout=5)
            # Last run
            last_run = conn.execute(
                "SELECT run_id, status, videos_produced, videos_uploaded, started_at "
                "FROM pipeline_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()

            # Today's stats
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            today_runs = conn.execute(
                "SELECT COUNT(*) FROM pipeline_runs WHERE started_at LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]
            today_uploads = conn.execute(
                "SELECT COUNT(*) FROM uploads WHERE uploaded_at LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]

            # Total stats
            total_runs = conn.execute("SELECT COUNT(*) FROM pipeline_runs").fetchone()[0]
            total_uploads = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
            total_articles = conn.execute("SELECT COUNT(*) FROM used_articles").fetchone()[0]

            conn.close()
        except Exception:
            last_run = None
            today_runs = today_uploads = total_runs = total_uploads = total_articles = 0

        lines = ["<b>📊 PIPELINE STATUS</b>", f"Time: {now}", ""]

        if last_run:
            status_icon = "✅" if last_run[1] == "completed" else "⚠️" if last_run[1] == "partial" else "❌"
            lines.extend([
                f"<b>Last Run:</b> {status_icon} {last_run[1]}",
                f"  Video: {'Yes' if last_run[2] else 'No'} | YouTube: {'Yes' if last_run[3] else 'No'}",
                f"  Time: {last_run[4]}",
            ])
        else:
            lines.append("<b>Last Run:</b> None yet")

        lines.extend([
            "",
            f"<b>Today:</b> {today_runs} runs, {today_uploads} uploads",
            f"<b>All-time:</b> {total_runs} runs, {total_uploads} uploads, {total_articles} articles",
        ])

        self._send("\n".join(lines))

    def _handle_runs(self, db_path: str):
        """Handle /runs command — show last 5 pipeline runs."""
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            rows = conn.execute(
                "SELECT run_id, status, videos_produced, videos_uploaded, started_at "
                "FROM pipeline_runs ORDER BY id DESC LIMIT 5"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []

        lines = ["<b>📋 LAST 5 RUNS</b>", ""]
        if rows:
            for r in rows:
                icon = "✅" if r[1] == "completed" else "⚠️" if r[1] == "partial" else "❌"
                yt = "📤" if r[3] else "💾"
                lines.append(f"{icon} <code>{r[0]}</code> | vid:{r[2]} {yt} | {r[4]}")
        else:
            lines.append("No runs recorded yet.")

        self._send("\n".join(lines))

    def _handle_uploads(self, db_path: str):
        """Handle /uploads command — show last 5 YouTube uploads."""
        try:
            conn = sqlite3.connect(db_path, timeout=5)
            rows = conn.execute(
                "SELECT youtube_video_id, title, upload_status, uploaded_at "
                "FROM uploads ORDER BY id DESC LIMIT 5"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []

        lines = ["<b>🎬 LAST 5 UPLOADS</b>", ""]
        if rows:
            for r in rows:
                title = (r[1] or "Untitled")[:40]
                url = f"https://youtube.com/watch?v={r[0]}" if r[0] else ""
                if url:
                    lines.append(f"  <a href=\"{url}\">{title}</a> ({r[2]})")
                else:
                    lines.append(f"  {title} ({r[2]})")
        else:
            lines.append("No uploads recorded yet.")

        self._send("\n".join(lines))

    def _handle_health(self, db_path: str):
        """Handle /health command — show system health."""

        # FFmpeg
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        ffmpeg_icon = "✅" if ffmpeg_ok else "❌"

        # Database
        db_ok = Path(db_path).exists()
        db_icon = "✅" if db_ok else "❌"
        db_size = ""
        if db_ok:
            try:
                db_size = f" ({Path(db_path).stat().st_size // 1024}KB)"
            except Exception:
                pass

        # API Keys
        groq_ok = bool(os.getenv("GROQ_API_KEY"))
        yt_ok = bool(os.getenv("YOUTUBE_REFRESH_TOKEN"))
        tg_ok = bool(os.getenv("TELEGRAM_BOT_TOKEN"))

        # Output files
        output = Path("output")
        videos = len(list((output / "videos").glob("*.mp4"))) if (output / "videos").exists() else 0

        lines = [
            "<b>🏥 SYSTEM HEALTH</b>",
            "",
            f"{ffmpeg_icon} FFmpeg: {'Available' if ffmpeg_ok else 'MISSING'}",
            f"{db_icon} Database: {db_size or 'Missing'}",
            f"{'✅' if groq_ok else '❌'} Groq API: {'Set' if groq_ok else 'MISSING'}",
            f"{'✅' if yt_ok else '❌'} YouTube: {'Configured' if yt_ok else 'Not configured'}",
            f"{'✅' if tg_ok else '❌'} Telegram: {'Configured' if tg_ok else 'Not configured'}",
            "",
            f"📁 Videos on disk: {videos}",
        ]

        self._send("\n".join(lines))

    def _handle_help(self):
        """Handle /help command — show available commands."""
        lines = [
            "<b>🤖 AI NEWS BOT COMMANDS</b>",
            "",
            "/status — Pipeline overview (last run, uploads today)",
            "/runs — Last 5 pipeline runs",
            "/uploads — Last 5 YouTube uploads",
            "/health — System health (FFmpeg, DB, API keys)",
            "/help — Show this message",
            "",
            "<i>Commands are checked every 30 seconds while the scheduler is running.</i>",
        ]
        self._send("\n".join(lines))


# Global singleton for easy access
notifier_instance: Optional[TelegramNotifier] = None


def get_notifier() -> TelegramNotifier:
    """Get or create the global notifier instance."""
    global notifier_instance
    if notifier_instance is None:
        notifier_instance = TelegramNotifier()
    return notifier_instance


def send_notification(message: str) -> bool:
    """Quick send a plain text notification (backward-compatible with scheduler)."""
    n = get_notifier()
    return n._send(message)


def notify_run_complete(result: dict, run_id: str = "") -> bool:
    """Send notification for a completed pipeline run."""
    n = get_notifier()
    if result.get("error"):
        return n.send_run_failure(
            run_id=run_id or result.get("run_id", "???"),
            error=result["error"],
            failed_step=result.get("current_step", ""),
        )
    return n.send_run_success(result, run_id)
