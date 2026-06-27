import sys
import asyncio
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import init_db
from workflows.pipeline import run_pipeline
from agents.notifier import get_notifier, notify_run_complete
from config import load_config, print_config_report
from health import print_health_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="AI News Pipeline")
    parser.add_argument("--mode", default="daily_news", choices=["daily_news", "shorts", "deep_dive"])
    parser.add_argument("--db", default=None)
    parser.add_argument("--health", action="store_true", help="Run health check and exit")
    parser.add_argument("--validate", action="store_true", help="Validate config and exit")
    args = parser.parse_args()

    config = load_config()

    if args.health:
        print_health_report(config.database_path)
        return

    if args.validate:
        print_config_report(config)
        return

    db_path = args.db or config.database_path
    init_db(db_path)
    result = asyncio.run(run_pipeline(mode=args.mode, config=config))

    # Send Telegram notification for standalone runs
    try:
        notifier = get_notifier()
        if notifier.enabled:
            notify_run_complete(result, run_id=result.get("run_id", "cli"))
    except Exception as e:
        logger.warning(f"Telegram notification failed: {e}")

    if result.get("error"):
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
