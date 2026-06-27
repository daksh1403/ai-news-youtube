"""
CASCADING LLM ROUTER — Never Stops
===================================
Tries providers in order. If one fails, tries the next.
If ALL cloud providers fail, uses local Ollama.

Chain: Groq → OpenRouter → Cerebras → Ollama (local, always works)
"""

import os
import time
import json
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ProviderState:
    name: str
    available: bool = True
    requests_today: int = 0
    tokens_today: int = 0
    last_error: str = ""
    last_error_time: float = 0
    cooldown_until: float = 0
    daily_limit: int = 999999
    token_limit: int = 999999999
    rpm_limit: int = 999
    requests_this_minute: int = 0
    minute_reset_time: float = 0


class LLMRouter:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_providers()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        if cls._instance is not None:
            cls._instance._init_providers()
            cls._instance.llm_cache.clear()
        cls._instance = None

    def _init_providers(self):
        self.providers = {
            "groq": ProviderState(
                name="groq",
                daily_limit=1000,
                token_limit=500000,
                rpm_limit=30,
            ),
            "openrouter": ProviderState(
                name="openrouter",
                daily_limit=200,
                token_limit=1000000,
                rpm_limit=20,
            ),
            "cerebras": ProviderState(
                name="cerebras",
                daily_limit=100,
                token_limit=1000000,
                rpm_limit=30,
            ),
            "ollama_local": ProviderState(
                name="ollama_local",
                daily_limit=999999,
                token_limit=999999999,
                rpm_limit=999,
            ),
        }

        self.llm_cache = {}
        self.provider_order = ["groq", "openrouter", "cerebras", "ollama_local"]

    def _get_llm(self, provider: str, model: str):
        cache_key = f"{provider}:{model}"
        if cache_key in self.llm_cache:
            return self.llm_cache[cache_key]

        llm = None
        if provider == "groq":
            api_key = os.getenv("GROQ_API_KEY")
            if api_key:
                try:
                    from langchain_groq import ChatGroq
                    llm = ChatGroq(model=model, groq_api_key=api_key, temperature=0, timeout=30)
                except ImportError:
                    logger.warning("langchain-groq not installed")

        elif provider == "openrouter":
            api_key = os.getenv("OPENROUTER_API_KEY")
            if api_key:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model=model,
                        api_key=api_key,
                        base_url="https://openrouter.ai/api/v1",
                        temperature=0,
                        timeout=30,
                    )
                except ImportError:
                    logger.warning("langchain-openai not installed")

        elif provider == "cerebras":
            api_key = os.getenv("CEREBRAS_API_KEY")
            if api_key:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model=model,
                        api_key=api_key,
                        base_url="https://api.cerebras.ai/v1",
                        temperature=0,
                        timeout=30,
                    )
                except ImportError:
                    logger.warning("langchain-openai not installed")

        elif provider == "ollama_local":
            try:
                import httpx
                resp = httpx.get("http://localhost:11434/api/tags", timeout=3)
                if resp.status_code != 200:
                    return None
            except Exception:
                return None
            try:
                from langchain_ollama import ChatOllama
                llm = ChatOllama(model=model, temperature=0, request_timeout=30)
            except ImportError:
                try:
                    from langchain_community.llms import Ollama
                    llm = Ollama(model=model, temperature=0)
                except ImportError:
                    logger.warning("langchain-ollama not installed")

        if llm:
            self.llm_cache[cache_key] = llm
        return llm

    def _is_provider_usable(self, provider_name: str) -> bool:
        state = self.providers[provider_name]
        now = time.time()

        if not state.available:
            if now > state.cooldown_until:
                state.available = True
                state.last_error = ""
            else:
                return False

        if now - state.minute_reset_time > 60:
            state.requests_this_minute = 0
            state.minute_reset_time = now

        if state.requests_this_minute >= state.rpm_limit:
            return False
        if state.requests_today >= state.daily_limit:
            return False

        return True

    def _record_success(self, provider_name: str, tokens: int = 0):
        state = self.providers[provider_name]
        state.requests_today += 1
        state.tokens_today += tokens
        state.requests_this_minute += 1

    def _record_failure(self, provider_name: str, error: str):
        state = self.providers[provider_name]
        state.last_error = error
        state.last_error_time = time.time()

        error_lower = error.lower()
        if "rate" in error_lower or "limit" in error_lower or "429" in error:
            state.available = False
            state.cooldown_until = time.time() + 300
            logger.warning(f"{provider_name} rate limited, cooling down 5 min")
        elif "auth" in error_lower or "key" in error_lower or "401" in error:
            state.available = False
            state.cooldown_until = time.time() + 3600
            logger.warning(f"{provider_name} auth failed, disabled 1 hour")
        elif "503" in error or "unavailable" in error_lower:
            state.available = False
            state.cooldown_until = time.time() + 120
            logger.warning(f"{provider_name} unavailable, retrying in 2 min")

    def _get_model_for_provider(self, provider: str, task: str = "general") -> str:
        models = {
            "groq": {
                "quality": "llama-3.3-70b-versatile",
                "general": "llama-3.1-8b-instant",
                "fast": "llama-3.1-8b-instant",
            },
            "openrouter": {
                "quality": "meta-llama/llama-3.3-70b-instruct:free",
                "general": "meta-llama/llama-3.1-8b-instruct:free",
                "fast": "meta-llama/llama-3.1-8b-instruct:free",
            },
            "cerebras": {
                "quality": "llama-3.3-70b",
                "general": "llama-3.1-8b",
                "fast": "llama-3.1-8b",
            },
            "ollama_local": {
                "quality": "phi4-mini",
                "general": "phi4-mini",
                "fast": "qwen3:1.7b",
            },
        }
        return models.get(provider, {}).get(task, "llama-3.1-8b-instant")

    async def invoke(self, prompt: str, task: str = "general", timeout: int = 60) -> str:
        for provider_name in self.provider_order:
            if not self._is_provider_usable(provider_name):
                continue

            model = self._get_model_for_provider(provider_name, task)
            llm = self._get_llm(provider_name, model)

            if not llm:
                continue

            try:
                response = await llm.ainvoke(prompt)
                content = response.content.strip()
                self._record_success(provider_name, len(content.split()))
                return content
            except Exception as e:
                error_str = str(e)
                self._record_failure(provider_name, error_str)
                logger.warning(f"{provider_name} failed: {error_str[:80]}")
                continue

        logger.warning("ALL providers failed, using local template fallback")
        return self._template_fallback(prompt)

    def _template_fallback(self, prompt: str) -> str:
        return json.dumps({
            "hook": "Breaking AI news you need to know about",
            "sections": [
                {"title": "Introduction", "content": "Let me break down the latest AI news for you.", "duration_seconds": 30},
                {"title": "Main Story", "content": "This is a developing story in artificial intelligence.", "duration_seconds": 300},
                {"title": "Why It Matters", "content": "Here's why this matters for the AI industry.", "duration_seconds": 120},
                {"title": "Conclusion", "content": "That's the latest in AI. Subscribe for daily updates!", "duration_seconds": 30},
            ],
            "cta": "Subscribe for daily AI news and drop a comment with your thoughts!",
            "full_script": "Breaking AI news you need to know about. Let me break down the latest AI news for you. This is a developing story in artificial intelligence. Here's why this matters for the AI industry. That's the latest in AI. Subscribe for daily updates and drop a comment with your thoughts!",
            "word_count": 55,
            "estimated_duration": 510,
        })

    def get_status(self) -> dict:
        return {
            name: {
                "available": state.available,
                "requests_today": state.requests_today,
                "tokens_today": state.tokens_today,
                "last_error": state.last_error[:50] if state.last_error else "",
                "cooldown_remaining": max(0, int(state.cooldown_until - time.time())),
            }
            for name, state in self.providers.items()
        }

    def reset_daily(self):
        for state in self.providers.values():
            state.requests_today = 0
            state.tokens_today = 0
            state.available = True
            state.cooldown_until = 0
