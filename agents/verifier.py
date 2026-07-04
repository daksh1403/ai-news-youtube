import json
import sqlite3
import logging
import asyncio
from datetime import datetime, timezone
from contextlib import contextmanager

from .tools.llm_router import LLMRouter
from .tools.moderation import moderate_content

logger = logging.getLogger(__name__)

SOURCE_SCORES = {
    "arxiv_ai": 0.95, "arxiv_cl": 0.95,
    "techcrunch_ai": 0.85, "venturebeat_ai": 0.80,
    "the_verge_ai": 0.80, "mit_tech_ai": 0.90,
    "openai_blog": 0.90, "huggingface_blog": 0.90,
    "techcrunch": 0.80, "arstechnica": 0.80,
    "wired": 0.80, "engadget": 0.75,
    "bbc_world": 0.85, "bbc_tech": 0.85,
    "cnn_top": 0.80, "guardian_world": 0.80,
    "nytimes_home": 0.85, "science_daily": 0.75,
    "nature_news": 0.90, "space": 0.80,
    "phys_org": 0.80, "bloomberg": 0.85,
    "cnbc_top": 0.80, "ft_world": 0.85,
    "variety": 0.75, "hollywood_reporter": 0.75,
    "deadline": 0.75, "espn": 0.80,
    "bbc_sport": 0.80,
}


class FactVerificationAgent:
    def __init__(self, db_path: str = "news_pipeline.db"):
        self.router = LLMRouter()
        self.db_path = db_path

    @contextmanager
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            yield conn
        finally:
            conn.close()

    async def verify(self, state: dict) -> dict:
        articles = state.get("deduplicated_articles", [])
        strict = state.get("content_moderation_strict", True)
        limit = state.get("verification_limit", 50)

        logger.info(f"Verifying {len(articles)} articles (strict={strict})...")

        verified = []
        blocked = 0
        flagged = 0
        review_queue = []

        # Process in batches with delays to avoid Groq rate limits (30 RPM)
        batch_size = 5
        for i, article in enumerate(articles[:limit]):
            # Add delay between batches to stay under rate limit
            if i > 0 and i % batch_size == 0:
                await asyncio.sleep(10)

            text = article.get("title", "") + " " + article.get("content", "")
            mod_result = moderate_content(
                title=article.get("title", ""),
                content=article.get("content", ""),
                source=article.get("source", ""),
                strict=strict,
            )

            if not mod_result.allowed:
                blocked += 1
                logger.warning(f"BLOCKED: {article['title'][:50]} — {mod_result.reason}")
                continue

            if mod_result.severity in ("medium", "low"):
                flagged += 1
                article["moderation_flag"] = mod_result.reason
                review_queue.append(article)

            score = await self._verify_article(article)
            article["verification_score"] = score
            verified.append(article)

        verified.sort(key=lambda x: x.get("verification_score", 0), reverse=True)

        if review_queue:
            self._save_review_queue(review_queue)

        logger.info(
            f"Verified {len(verified)} | Blocked {blocked} | Flagged {flagged} | "
            f"Review queue: {len(review_queue)}"
        )

        return {
            **state,
            "verified_articles": verified,
            "blocked_count": blocked,
            "flagged_count": flagged,
            "review_queue_size": len(review_queue),
            "current_step": "ranker",
        }

    def _save_review_queue(self, articles: list):
        try:
            with self._get_conn() as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS review_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        article_url TEXT,
                        article_title TEXT,
                        category TEXT,
                        flag_reason TEXT,
                        verification_score REAL,
                        status TEXT DEFAULT 'pending',
                        reviewed_at TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                for article in articles:
                    conn.execute(
                        "INSERT OR IGNORE INTO review_queue (article_url, article_title, category, flag_reason, verification_score) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            article.get("url", ""),
                            article.get("title", "")[:200],
                            article.get("category", ""),
                            article.get("moderation_flag", ""),
                            article.get("verification_score", 0),
                        ),
                    )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to save review queue: {e}")

    async def _verify_article(self, article: dict) -> float:
        prompt = f"""Rate the credibility of this news article on a scale of 0.0 to 1.0.

Title: {article['title']}
Source: {article['source']}
Content preview: {article['content'][:500]}

Consider:
- Is this from a reputable source?
- Does the title match the content?
- Are there specific facts/numbers cited?
- Is this likely real news vs opinion/rumor?

Return ONLY a number between 0.0 and 1.0, nothing else."""

        try:
            content = await self.router.invoke(prompt, task="fast")
            score = float(content.strip())
            return max(0.0, min(1.0, score))
        except Exception:
            return SOURCE_SCORES.get(article.get("source", ""), 0.7)
