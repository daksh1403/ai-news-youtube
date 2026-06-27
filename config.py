import os
import sys
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Config:
    # LLM
    groq_api_key: str = ""
    openrouter_api_key: str = ""

    # YouTube
    youtube_api_key: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_refresh_token: str = ""

    # Database
    database_path: str = "news_pipeline.db"

    # TTS
    tts_voice: str = "en-US-ChristopherNeural"
    tts_engine: str = "edge-tts"

    # Image
    image_provider: str = "pollinations"
    together_api_key: str = ""

    # Scheduling
    videos_per_day: int = 2
    pipeline_run_hours: list = field(default_factory=lambda: [6, 14])

    # Content Safety
    require_human_review: bool = False
    content_moderation_strict: bool = True
    max_articles_per_run: int = 50

    # Notifications
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    discord_webhook_url: str = ""

    # YouTube Safety
    auto_upload: bool = False
    review_before_upload: bool = True

    # Derived
    has_groq: bool = False
    has_youtube_upload: bool = False
    has_notifications: bool = False


_config: Optional[Config] = None


def _parse_run_hours(value: str) -> list:
    """Parse comma-separated run hours from env var."""
    try:
        hours = [int(h.strip()) for h in value.split(",") if h.strip()]
        return sorted(set(h for h in hours if 0 <= h <= 23))
    except (ValueError, AttributeError):
        return [6, 14]


def load_config(env_path: str = ".env") -> Config:
    global _config
    if _config is not None:
        return _config

    env_file = Path(env_path)
    if env_file.exists():
        _parse_env_file(env_file)

    _config = Config(
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        youtube_api_key=os.getenv("YOUTUBE_API_KEY", ""),
        youtube_client_id=os.getenv("YOUTUBE_CLIENT_ID", ""),
        youtube_client_secret=os.getenv("YOUTUBE_CLIENT_SECRET", ""),
        youtube_refresh_token=os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
        database_path=os.getenv("DATABASE_PATH", "news_pipeline.db"),
        tts_voice=os.getenv("TTS_VOICE", "en-US-ChristopherNeural"),
        tts_engine=os.getenv("TTS_ENGINE", "edge-tts"),
        image_provider=os.getenv("IMAGE_PROVIDER", "pollinations"),
        together_api_key=os.getenv("TOGETHER_API_KEY", ""),
        videos_per_day=int(os.getenv("VIDEOS_PER_DAY", "2")),
        pipeline_run_hours=_parse_run_hours(os.getenv("PIPELINE_RUN_HOURS", "6,14")),
        require_human_review=os.getenv("REQUIRE_HUMAN_REVIEW", "false").lower() == "true",
        content_moderation_strict=os.getenv("CONTENT_MODERATION_STRICT", "true").lower() == "true",
        max_articles_per_run=int(os.getenv("MAX_ARTICLES_PER_RUN", "50")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
        auto_upload=os.getenv("AUTO_UPLOAD", "false").lower() == "true",
        review_before_upload=os.getenv("REVIEW_BEFORE_UPLOAD", "true").lower() == "true",
    )

    _config.has_groq = bool(_config.groq_api_key)
    _config.has_youtube_upload = bool(
        _config.youtube_client_id and _config.youtube_client_secret
    )
    _config.has_notifications = bool(
        (_config.telegram_bot_token and _config.telegram_chat_id)
        or _config.discord_webhook_url
    )

    return _config


def _parse_env_file(path: Path):
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if value:
                    os.environ.setdefault(key, value)
    except Exception as e:
        logger.warning(f"Failed to parse {path}: {e}")


def get_config() -> Config:
    if _config is None:
        return load_config()
    return _config


def validate_config(config: Config) -> list:
    warnings = []
    errors = []

    if not config.has_groq:
        warnings.append("No GROQ_API_KEY — scripts will use template fallback (generic content)")

    if not config.has_youtube_upload:
        warnings.append("No YouTube OAuth — uploads will be skipped (videos saved locally)")

    if config.auto_upload and not config.has_youtube_upload:
        errors.append("AUTO_UPLOAD=true but YouTube OAuth not configured")

    if config.videos_per_day < 1 or config.videos_per_day > 10:
        warnings.append(f"VIDEOS_PER_DAY={config.videos_per_day} is unusual (1-10 recommended)")

    if not config.pipeline_run_hours:
        warnings.append("No pipeline run hours configured")

    return warnings, errors


def print_config_report(config: Config):
    warnings, errors = validate_config(config)

    print("\n" + "=" * 60)
    print("  AI NEWS PIPELINE — CONFIGURATION")
    print("=" * 60)

    print(f"\n  LLM:")
    print(f"    Groq:      {'OK' if config.has_groq else 'NOT CONFIGURED'}")
    print(f"    OpenRouter: {'OK' if config.openrouter_api_key else 'not set'}")

    print(f"\n  YouTube:")
    print(f"    Upload:    {'OK' if config.has_youtube_upload else 'DISABLED (no OAuth)'}")
    print(f"    Auto:      {'YES' if config.auto_upload else 'NO (manual review)'}")

    print(f"\n  Content Safety:")
    print(f"    Moderation: {'STRICT' if config.content_moderation_strict else 'standard'}")
    print(f"    Human review: {'REQUIRED' if config.require_human_review else 'optional'}")
    print(f"    Max articles: {config.max_articles_per_run}")

    print(f"\n  Schedule:")
    print(f"    Videos/day: {config.videos_per_day}")
    hours_str = ', '.join(f'{h:02d}:00' for h in config.pipeline_run_hours)
    print(f"    Run hours: {hours_str}")

    print(f"\n  Notifications:")
    print(f"    Telegram:  {'OK' if config.telegram_bot_token else 'not set'}")
    print(f"    Discord:   {'OK' if config.discord_webhook_url else 'not set'}")

    if warnings:
        print(f"\n  WARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"    ⚠ {w}")

    if errors:
        print(f"\n  ERRORS ({len(errors)}):")
        for e in errors:
            print(f"    ✗ {e}")

    print("\n" + "=" * 60)
    print()
