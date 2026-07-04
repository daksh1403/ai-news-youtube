import time
import sqlite3
import logging
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class AnalyticsAgent:
    def __init__(self, db_path: str = "news_pipeline.db"):
        self.db_path = db_path

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    async def analyze(self, state: dict) -> dict:
        run_id = state.get("run_id", "")
        video_id = state.get("youtube_video_id", "")

        logger.info("Recording pipeline run...")

        self._record_run(state)
        self._mark_article_used(state)

        if video_id and video_id != "local_only":
            self._record_upload(state)

        logger.info("Run recorded")
        return {**state, "current_step": "learner"}

    def _record_run(self, state: dict):
        try:
            with self._get_conn() as conn:
                # Calculate actual pipeline duration from start time
                start_time = state.get("pipeline_started_at", 0)
                if start_time:
                    duration = round(time.time() - start_time, 1)
                else:
                    duration = 0

                # Determine status
                if state.get("error"):
                    status = "failed"
                elif state.get("youtube_video_id"):
                    status = "completed"
                elif state.get("video_path"):
                    status = "completed"
                elif state.get("deduplicated_articles"):
                    status = "partial"
                else:
                    status = "partial"

                conn.execute("""
                    INSERT INTO pipeline_runs (run_id, started_at, completed_at, status,
                        articles_collected, scripts_generated, videos_produced, videos_uploaded, errors, duration_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.get("run_id", ""),
                    datetime.now(timezone.utc).isoformat(),
                    datetime.now(timezone.utc).isoformat(),
                    status,
                    len(state.get("deduplicated_articles", [])),
                    1 if state.get("script") else 0,
                    1 if state.get("video_path") else 0,
                    1 if state.get("youtube_video_id") else 0,
                    str(state.get("errors", [])),
                    duration,
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"DB error recording run: {e}")

    def _mark_article_used(self, state: dict):
        article = state.get("selected_article", {})
        if not article or not article.get("url"):
            return

        try:
            with self._get_conn() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO used_articles (article_url, article_title, video_path, youtube_video_id) VALUES (?, ?, ?, ?)",
                    (
                        article.get("url", ""),
                        article.get("title", ""),
                        state.get("video_path", ""),
                        state.get("youtube_video_id", ""),
                    )
                )
                conn.commit()
                logger.info(f"Marked article as used: {article['title'][:50]}")
        except Exception as e:
            logger.error(f"Failed to mark article as used: {e}")

    def _record_upload(self, state: dict):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO uploads (video_id, youtube_video_id, youtube_url, title,
                        description, tags, category, upload_status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.get("run_id", ""),
                    state.get("youtube_video_id", ""),
                    state.get("youtube_url", ""),
                    state.get("seo_metadata", {}).get("title", ""),
                    state.get("seo_metadata", {}).get("description", ""),
                    str(state.get("seo_metadata", {}).get("tags", [])),
                    "22",
                    "uploaded",
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Upload record error: {e}")
