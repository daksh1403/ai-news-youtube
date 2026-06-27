import json
import re
import logging

from .tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)


def sanitize_seo_text(text: str, max_length: int) -> str:
    text = re.sub(r'[<>"\';`\\]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:max_length]


class SEOAgent:
    def __init__(self):
        self.router = LLMRouter()

    async def optimize(self, state: dict) -> dict:
        article = state.get("selected_article", {})
        if not article:
            return {**state, "seo_metadata": {}, "current_step": "scriptwriter"}

        logger.info(f"Optimizing Shorts metadata for: {article['title'][:50]}...")

        category = article.get("category", "general")

        prompt = f"""Generate YouTube Shorts SEO metadata for this news video.

Title: {article['title']}
Content: {article['content'][:1000]}
Category: {category}

YOUTUBE SHORTS SEO REQUIREMENTS:
- title: max 40 chars, front-loaded keywords, curiosity hook
  * Use trending formats: "Wait, what?!", "This is HUGE", "Breaking"
  * Include emoji in title for CTR boost
  * Example: "AI Just Did WHAT?! 🤯" or "This Changes Everything 🔥"
- description: 2-3 lines, first line is hook, include hashtags
- tags: 10-15 tags mixing broad and specific
- hashtags: 3-5 hashtags (required for Shorts discovery)

Return ONLY valid JSON."""

        try:
            content = await self.router.invoke(prompt, task="general")
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            seo = json.loads(content)
            seo["title"] = sanitize_seo_text(seo.get("title", ""), 40)
            seo["description"] = sanitize_seo_text(seo.get("description", ""), 500)
            seo["tags"] = [sanitize_seo_text(t, 30) for t in seo.get("tags", [])[:15]]
        except Exception as e:
            logger.warning(f"LLM error: {e}, using defaults")
            seo = {
                "title": sanitize_seo_text(f"{article['title'][:30]} 🔥", 40),
                "description": sanitize_seo_text(f"{article['title']}\n\nFollow for more {category} news!", 500),
                "tags": [category, "news", "shorts", "viral", "trending", "breaking"],
                "hashtags": ["#shorts", f"#{category}", "#news", "#viral", "#trending"],
            }

        logger.info(f"Title: {seo.get('title', '')[:40]}")
        return {**state, "seo_metadata": seo, "current_step": "scriptwriter"}
