import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database import get_db

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def collect():
    with get_db() as conn:
        runs = conn.execute("""
            SELECT run_id, status, articles_collected, videos_produced,
                   videos_uploaded, completed_at
            FROM pipeline_runs
            ORDER BY completed_at DESC
            LIMIT 10
        """).fetchall()

        logger.info("\n=== Recent Pipeline Runs ===")
        for r in runs:
            logger.info(f"  {r['completed_at']} | {r['status']:10s} | articles={r['articles_collected']} | videos={r['videos_produced']} | uploaded={r['videos_uploaded']}")

        uploads = conn.execute("""
            SELECT youtube_video_id, title, uploaded_at, upload_status
            FROM uploads
            ORDER BY uploaded_at DESC
            LIMIT 10
        """).fetchall()

        logger.info("\n=== Recent Uploads ===")
        for u in uploads:
            logger.info(f"  {u['uploaded_at']} | {u['upload_status']:10s} | {u['title'][:50]} | {u['youtube_video_id']}")

        insights = conn.execute("""
            SELECT insight_type, insight_data, created_at
            FROM learning_insights
            ORDER BY created_at DESC
            LIMIT 5
        """).fetchall()

        logger.info("\n=== Learning Insights ===")
        for i in insights:
            logger.info(f"  {i['created_at']} | {i['insight_type']}: {i['insight_data'][:100]}")


if __name__ == "__main__":
    collect()
