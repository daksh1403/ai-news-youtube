import hashlib
import sqlite3
import logging
from typing import List
from pathlib import Path

from .tools.rss_parser import RSSParser

logger = logging.getLogger(__name__)


class NewsCollectorAgent:
    def __init__(self, db_path: str = "news_pipeline.db", verification_limit: int = 50):
        self.rss = RSSParser()
        self.db_path = db_path
        self.verification_limit = verification_limit

    def _get_used_urls(self) -> set:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT article_url FROM used_articles").fetchall()
            conn.close()
            return {row[0] for row in rows}
        except Exception as e:
            logger.warning(f"Could not load used articles: {e}")
            return set()

    def _get_used_titles(self) -> set:
        try:
            conn = sqlite3.connect(self.db_path)
            rows = conn.execute("SELECT article_title FROM used_articles WHERE article_title IS NOT NULL").fetchall()
            conn.close()
            return {row[0].lower().strip()[:80] for row in rows}
        except Exception as e:
            logger.warning(f"Could not load used titles: {e}")
            return set()

    def mark_used(self, article: dict, video_path: str = "", youtube_video_id: str = ""):
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                "INSERT OR IGNORE INTO used_articles (article_url, article_title, video_path, youtube_video_id) VALUES (?, ?, ?, ?)",
                (article.get("url", ""), article.get("title", ""), video_path, youtube_video_id)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to mark article as used: {e}")

    async def collect(self, state: dict) -> dict:
        logger.info("Fetching news from all sources...")
        articles = self.rss.fetch_all(hours=48)

        deduplicated = self._deduplicate(articles)

        used_urls = self._get_used_urls()
        used_titles = self._get_used_titles()

        fresh = []
        skipped = 0
        for a in deduplicated:
            a["id"] = hashlib.sha256(a["url"].encode()).hexdigest()
            title_key = a["title"].lower().strip()[:80]
            if a["url"] not in used_urls and title_key not in used_titles:
                fresh.append(a)
            else:
                skipped += 1

        logger.info(f"Collected {len(articles)} raw, {len(deduplicated)} after dedup, {len(fresh)} new ({skipped} already used)")

        return {
            **state,
            "raw_articles": articles,
            "deduplicated_articles": fresh,
            "current_step": "trend_detector",
        }

    def _deduplicate(self, articles: List[dict]) -> List[dict]:
        seen_titles = set()
        seen_urls = set()
        unique = []

        for article in articles:
            title_key = article["title"].lower().strip()[:80]
            url_key = article["url"]

            if title_key in seen_titles or url_key in seen_urls:
                continue

            seen_titles.add(title_key)
            seen_urls.add(url_key)
            unique.append(article)

        return unique
