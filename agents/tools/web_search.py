import httpx
import logging
from typing import List

logger = logging.getLogger(__name__)


class WebSearcher:
    def __init__(self):
        self.client = httpx.Client(timeout=15, follow_redirects=True)

    def search(self, query: str, max_results: int = 5) -> List[dict]:
        try:
            url = "https://api.duckduckgo.com/"
            params = {"q": query, "format": "json", "no_html": 1, "skip_disambig": 1}
            resp = self.client.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for result in data.get("RelatedTopics", [])[:max_results]:
                if isinstance(result, dict) and "Text" in result:
                    results.append({
                        "title": result.get("Text", "")[:100],
                        "snippet": result.get("Text", ""),
                        "url": result.get("FirstURL", ""),
                    })
            return results
        except Exception as e:
            logger.error(f"WebSearch error: {e}")
            return []

    def verify_claim(self, claim: str) -> dict:
        results = self.search(claim, max_results=3)
        return {
            "claim": claim,
            "sources_found": len(results),
            "sources": results,
            "likely_true": len(results) >= 2,
        }
