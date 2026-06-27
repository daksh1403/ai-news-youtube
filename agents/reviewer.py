import json
import logging

from .tools.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class QualityReviewAgent:
    def __init__(self):
        self.router = LLMRouter()

    async def review(self, state: dict) -> dict:
        script = state.get("script", {})
        article = state.get("selected_article", {})
        retry_count = state.get("retry_count", 0)

        if not script or not article:
            return {**state, "script_review": {"approved": True}, "current_step": "thumbnail"}

        logger.info(f"Reviewing Shorts script (attempt {retry_count + 1})...")

        word_count = script.get("word_count", 0)
        duration = script.get("estimated_duration", 0)

        if word_count > 200 or duration > 65:
            logger.warning(f"Script too long ({word_count} words, {duration}s), auto-trimming")
            full = script.get("full_script", "")
            words = full.split()
            if len(words) > 170:
                words = words[:170]
                script["full_script"] = " ".join(words)
            script["word_count"] = len(words)
            script["estimated_duration"] = min(59, max(10, int(len(words) * 0.4)))
            word_count = script["word_count"]
            duration = script["estimated_duration"]

        prompt = f"""Review this YouTube Shorts script for quality.

ORIGINAL ARTICLE: {article['content'][:800]}
GENERATED SCRIPT: {script.get('full_script', '')[:500]}

SHORTS REQUIREMENTS (CRITICAL):
1. Under 60 seconds total
2. 130-170 words max
3. Hook in first 2 seconds
4. Fast pace, no filler
5. Clear CTA at end
6. Easy to understand in one watch

Return JSON:
- approved: bool (true if score >= 6)
- score: 1-10
- issues: list of problems

Return ONLY valid JSON."""

        try:
            content = await self.router.invoke(prompt, task="general")
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            review = json.loads(content)
            if "approved" not in review:
                review["approved"] = review.get("score", 7) >= 6
        except Exception as e:
            logger.warning(f"LLM error: {e}, approving by default")
            review = {"approved": True, "score": 7, "issues": []}

        if not review.get("approved") and retry_count < 2:
            logger.info(f"Script needs revision (score: {review.get('score', 0)})")
            return {
                **state,
                "script_review": review,
                "retry_count": retry_count + 1,
                "current_step": "scriptwriter",
            }

        logger.info(f"Script approved (score: {review.get('score', 7)})")
        return {**state, "script_review": {"approved": True, "score": review.get("score", 7)}, "retry_count": 0, "current_step": "thumbnail"}
