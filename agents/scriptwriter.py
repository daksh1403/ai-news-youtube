import json
import logging

from .tools.llm_router import LLMRouter
from .tools.scripts import build_script_from_article, get_llm_fallback_response

logger = logging.getLogger(__name__)


class ScriptWriterAgent:
    def __init__(self):
        self.router = LLMRouter()

    async def write_script(self, state: dict) -> dict:
        article = state.get("selected_article", {})
        if not article:
            return {**state, "script": {}, "current_step": "reviewer"}

        logger.info(f"Writing Shorts script for: {article['title'][:50]}...")

        category = article.get("category", "general")

        prompt = f"""Write a YouTube Shorts script about this news.

ARTICLE:
Title: {article['title']}
Source: {article['source']}
Category: {category}
Content: {article['content'][:3000]}

YOUTUBE SHORTS REQUIREMENTS (CRITICAL):
- Total length: 45-59 seconds MAX (under 60 seconds)
- Word count: 130-170 words MAX
- Hook in first 2 seconds (shock/curiosity/value)
- Fast pace, no pauses, every second counts
- Structure: Hook (2s) → Context (10s) → Main Point (20s) → Why It Matters (10s) → CTA (5s)
- Tone: energetic, punchy, like telling a friend breaking news
- End with: "Follow for more!" or "Subscribe!"
- NO filler words, NO "um", NO "so basically"
- Every word must earn its place

Return JSON with:
- hook: the opening line (2 seconds max)
- body: main content (40 seconds)
- cta: closing call to action (5 seconds)
- full_script: complete narration text (all parts combined, 130-170 words)
- word_count: exact word count
- estimated_duration: total seconds (must be < 60)

Return ONLY valid JSON."""

        try:
            content = await self.router.invoke(prompt, task="quality")
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "full_script" in parsed:
                script = parsed
                wc = script.get("word_count", 0)
                dur = script.get("estimated_duration", 0)
                if wc > 200 or dur > 65:
                    logger.warning(f"LLM script too long ({wc}w, {dur}s), using improved fallback")
                    script = build_script_from_article(article)
            else:
                script = build_script_from_article(article)
        except Exception as e:
            logger.warning(f"LLM error: {e}, using improved fallback script")
            script = build_script_from_article(article)

        logger.info(f"Script: {script.get('word_count', 0)} words, {script.get('estimated_duration', 0)}s")
        return {**state, "script": script, "current_step": "reviewer"}
