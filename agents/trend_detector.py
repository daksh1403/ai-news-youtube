import json
import logging

from .tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class TrendDetectorAgent:
    def __init__(self):
        self.router = LLMRouter()

    async def detect(self, state: dict) -> dict:
        articles = state.get("deduplicated_articles", [])
        if not articles:
            return {**state, "trends": [], "current_step": "verifier"}

        logger.info(f"Analyzing {len(articles)} articles across categories...")

        by_category = {}
        for a in articles:
            cat = a.get("category", "general")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(a)

        category_summary = "\n".join([
            f"  {cat}: {len(arts)} articles" for cat, arts in by_category.items()
        ])

        top_articles = "\n".join([
            f"- [{a.get('category', '?')}] {a['title']} ({a['source']})" for a in articles[:40]
        ])

        prompt = f"""Analyze these news articles and identify the top trending topics across ALL categories.

CATEGORIES:
{category_summary}

TOP ARTICLES:
{top_articles}

Return a JSON array of the top 5 trends. Each trend object:
- topic: string (short topic name)
- category: string (ai/tech/world/science/business/entertainment/sports)
- velocity: 1-10 (how fast growing)
- impact: 1-10 (industry impact)
- novelty: 1-10 (how new)
- article_titles: list of related article titles (exact matches from above)

Return ONLY valid JSON array, no other text."""

        trends = self._build_fallback_trends(articles)

        try:
            content = await self.router.invoke(prompt, task="general")
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)
            if isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
                trends = parsed
            else:
                logger.warning("LLM returned non-list trend data, using fallback")
        except Exception as e:
            logger.warning(f"Parse error: {e}, using fallback")

        logger.info(f"Found {len(trends)} trends")
        return {**state, "trends": trends, "current_step": "verifier"}

    def _build_fallback_trends(self, articles: list) -> list:
        best_by_category = {}
        for a in articles:
            cat = a.get("category", "general")
            if cat not in best_by_category:
                best_by_category[cat] = a

        return [{
            "topic": a["title"][:60],
            "category": a.get("category", "general"),
            "velocity": 5,
            "impact": 5,
            "novelty": 5,
            "article_titles": [a["title"]],
        } for a in list(best_by_category.values())[:5]]
