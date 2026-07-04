import feedparser
import httpx
import logging
import hashlib
import time
import random
from datetime import datetime, timedelta, timezone
from typing import List

logger = logging.getLogger(__name__)


class RSSParser:
    AI_SOURCES = {
        "arxiv_ai": "http://arxiv.org/rss/cs.AI",
        "arxiv_cl": "http://arxiv.org/rss/cs.CL",
        "techcrunch_ai": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "venturebeat_ai": "https://venturebeat.com/category/ai/feed/",
        "the_verge_ai": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "mit_tech_ai": "https://www.technologyreview.com/feed/",
        "openai_blog": "https://openai.com/blog/rss.xml",
        "huggingface_blog": "https://huggingface.co/blog/feed.xml",
    }

    TECH_SOURCES = {
        "techcrunch": "https://techcrunch.com/feed/",
        "the_verge": "https://www.theverge.com/rss/index.xml",
        "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
        "wired": "https://www.wired.com/feed/rss",
        "engadget": "https://www.engadget.com/rss.xml",
    }

    GENERAL_NEWS = {
        "bbc_world": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "bbc_tech": "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "cnn_top": "http://rss.cnn.com/rss/edition.rss",
        "guardian_world": "https://www.theguardian.com/world/rss",
        "nytimes_home": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    }

    SCIENCE_SOURCES = {
        "science_daily": "https://www.sciencedaily.com/rss/all.xml",
        "nature_news": "https://www.nature.com/nature.rss",
        "space": "https://www.space.com/feeds/all",
        "phys_org": "https://phys.org/rss-feed/",
    }

    BUSINESS_SOURCES = {
        "bloomberg": "https://feeds.bloomberg.com/markets/news.rss",
        "cnbc_top": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114",
        "ft_world": "https://www.ft.com/rss/home",
    }

    ENTERTAINMENT_SOURCES = {
        "variety": "https://variety.com/feed/",
        "hollywood_reporter": "https://www.hollywoodreporter.com/feed/",
        "deadline": "https://deadline.com/feed/",
    }

    SPORTS_SOURCES = {
        "espn": "https://www.espn.com/espn/rss/news",
        "bbc_sport": "https://feeds.bbci.co.uk/sport/rss.xml",
    }

    ALL_SOURCES = {}
    ALL_SOURCES.update(AI_SOURCES)
    ALL_SOURCES.update(TECH_SOURCES)
    ALL_SOURCES.update(GENERAL_NEWS)
    ALL_SOURCES.update(SCIENCE_SOURCES)
    ALL_SOURCES.update(BUSINESS_SOURCES)
    ALL_SOURCES.update(ENTERTAINMENT_SOURCES)
    ALL_SOURCES.update(SPORTS_SOURCES)

    SOURCE_CATEGORIES = {}
    for name in AI_SOURCES:
        SOURCE_CATEGORIES[name] = "ai"
    for name in TECH_SOURCES:
        SOURCE_CATEGORIES[name] = "tech"
    for name in GENERAL_NEWS:
        SOURCE_CATEGORIES[name] = "world"
    for name in SCIENCE_SOURCES:
        SOURCE_CATEGORIES[name] = "science"
    for name in BUSINESS_SOURCES:
        SOURCE_CATEGORIES[name] = "business"
    for name in ENTERTAINMENT_SOURCES:
        SOURCE_CATEGORIES[name] = "entertainment"
    for name in SPORTS_SOURCES:
        SOURCE_CATEGORIES[name] = "sports"

    def __init__(self):
        self.client = httpx.Client(
            timeout=30,
            headers={"User-Agent": "AINewsBot/1.0 (+https://github.com/ai-news-youtube; academic research)"},
            follow_redirects=True,
        )

    def fetch_all(self, hours: int = 48) -> List[dict]:
        """Fetch articles from all RSS sources. Non-blocking where possible."""
        import concurrent.futures

        articles = []
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        source_list = list(self.ALL_SOURCES.items())
        random.shuffle(source_list)

        # Use thread pool for parallel fetching to avoid blocking the event loop
        def fetch_one(args):
            source_name, url = args
            try:
                return self._fetch_feed(url, source_name, cutoff)
            except Exception as e:
                logger.error(f"Error fetching {source_name}: {e}")
                return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_one, item): item for item in source_list}
            for future in concurrent.futures.as_completed(futures):
                try:
                    items = future.result(timeout=30)
                    if items:
                        articles.extend(items)
                except concurrent.futures.TimeoutError:
                    logger.warning(f"Feed fetch timed out: {futures[future][0]}")
                except Exception as e:
                    logger.error(f"Feed fetch error: {e}")

        return articles

    def _fetch_feed(self, url: str, source: str, cutoff: datetime) -> List[dict]:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.get(url, timeout=30)
                response.raise_for_status()
                break
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                if attempt < max_retries - 1:
                    wait = (attempt + 1) * 2 + random.uniform(0, 1)
                    logger.warning(f"Retry {attempt+1}/{max_retries} for {source}: {e}")
                    time.sleep(wait)
                else:
                    logger.error(f"Failed fetching {source} after {max_retries} attempts: {e}")
                    return []

        feed = feedparser.parse(response.text)
        articles = []

        for entry in feed.entries:
            pub_date = self._parse_date(entry)
            if pub_date and pub_date < cutoff:
                continue

            content = self._extract_content(entry)
            if not content or len(content) < 50:
                continue

            article = {
                "title": entry.get("title", "").strip(),
                "content": content,
                "url": entry.get("link", ""),
                "source": source,
                "category": self.SOURCE_CATEGORIES.get(source, "general"),
                "author": entry.get("author", ""),
                "published_at": pub_date.isoformat() if pub_date else datetime.now(timezone.utc).isoformat(),
                "external_id": hashlib.md5(entry.get("link", entry.get("title", "")).encode()).hexdigest(),
                "word_count": len(content.split()),
            }

            if article["title"]:
                articles.append(article)

        return articles

    def _extract_content(self, entry) -> str:
        if hasattr(entry, "summary"):
            return self._clean_html(entry.summary)
        if hasattr(entry, "content"):
            return self._clean_html(entry.content[0].get("value", ""))
        return ""

    def _clean_html(self, html: str) -> str:
        import re
        clean = re.sub(r"<[^>]+>", " ", html)
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean[:5000]

    def _parse_date(self, entry) -> datetime:
        for field in ["published_parsed", "updated_parsed"]:
            parsed = getattr(entry, field, None)
            if parsed:
                try:
                    from time import mktime
                    dt = datetime.fromtimestamp(mktime(parsed), tz=timezone.utc)
                    return dt
                except Exception:
                    continue
        return None
