import sqlite3
import json
import logging
from datetime import datetime, timezone
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class LearningAgent:
    def __init__(self, db_path: str = "news_pipeline.db"):
        self.db_path = db_path

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    async def learn(self, state: dict) -> dict:
        logger.info("Analyzing performance patterns...")

        history = self._load_history()
        if len(history) < 3:
            logger.info("Not enough history yet, skipping")
            return {**state, "learning_insights": {}, "completed": True}

        insights = self._analyze_patterns(history)
        self._save_insights(insights)

        logger.info(f"Insights: {list(insights.keys())}")
        return {**state, "learning_insights": insights, "completed": True}

    def _load_history(self) -> list:
        try:
            with self._get_conn() as conn:
                rows = conn.execute("""
                    SELECT status, articles_collected, videos_produced, videos_uploaded,
                           duration_seconds, errors, completed_at
                    FROM pipeline_runs
                    ORDER BY completed_at DESC
                    LIMIT 20
                """).fetchall()
                return [{
                    "status": r[0], "articles": r[1], "videos": r[2],
                    "uploaded": r[3], "duration": r[4], "errors": r[5], "date": r[6],
                } for r in rows]
        except Exception as e:
            logger.error(f"Failed to load history: {e}")
            return []

    def _analyze_patterns(self, history: list) -> dict:
        total = len(history)
        success = sum(1 for h in history if h["status"] == "completed")
        uploaded = sum(1 for h in history if h.get("uploaded", 0) > 0)
        avg_articles = sum(h.get("articles", 0) for h in history) / max(total, 1)

        return {
            "success_rate": round(success / max(total, 1) * 100, 1),
            "upload_rate": round(uploaded / max(total, 1) * 100, 1),
            "avg_articles_collected": round(avg_articles, 1),
            "total_runs": total,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _save_insights(self, insights: dict):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    INSERT INTO learning_insights (insight_type, insight_data, confidence, applied)
                    VALUES (?, ?, ?, ?)
                """, (
                    "performance_summary",
                    json.dumps(insights),
                    insights.get("success_rate", 0) / 100,
                    1,
                ))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save insights: {e}")
