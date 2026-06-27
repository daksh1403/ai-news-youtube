import json
import logging

from .tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class NewsRankingAgent:
    def __init__(self):
        self.router = LLMRouter()

    async def rank(self, state: dict) -> dict:
        articles = state.get("verified_articles", [])
        if not articles:
            return {**state, "ranked_articles": [], "selected_article": {}, "current_step": "seo_optimizer"}

        logger.info(f"Ranking {len(articles)} articles for Shorts...")

        articles_text = "\n".join([
            f"{i+1}. [{a.get('category', '?')}] [{a.get('verification_score', 0.7):.1f}] {a['title']} ({a['source']})"
            for i, a in enumerate(articles[:15])
        ])

        prompt = f"""Rank these news articles for a YouTube Shorts video. Pick the SINGLE BEST article.

Articles:
{articles_text}

SHORTS RANKING CRITERIA:
1. Hook potential (can grab attention in 2 seconds?)
2. Viral potential (will people share this?)
3. Simplicity (can explain in under 60 seconds?)
4. Visual potential (interesting images/footage?)
5. Universal appeal (not too niche?)
6. Category diversity (prefer variety)

CRITICAL: The article MUST be explainable in 130-170 words (under 60 seconds).
Avoid complex topics that need long explanation.

Return JSON with:
- ranked_indices: list of article numbers in ranking order (1-indexed)
- best_index: the single best article number
- reason: why this is the best pick for a Short

Return ONLY valid JSON."""

        result = {}
        try:
            content = await self.router.invoke(prompt, task="general")
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            result = json.loads(content)
            best_idx = result.get("best_index", 1) - 1
        except Exception as e:
            logger.warning(f"LLM error: {e}, using fallback")
            best_idx = 0

        best_idx = max(0, min(best_idx, len(articles) - 1))
        selected = articles[best_idx]

        ranked = [articles[i-1] for i in result.get("ranked_indices", range(1, len(articles)+1))
                  if 1 <= i <= len(articles)] if result else articles

        logger.info(f"Selected: [{selected.get('category', '?')}] {selected['title'][:60]}")
        return {
            **state,
            "ranked_articles": ranked,
            "selected_article": selected,
            "current_step": "seo_optimizer",
        }
