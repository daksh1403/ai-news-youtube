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
