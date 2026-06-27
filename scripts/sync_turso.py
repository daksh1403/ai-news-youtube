"""
Sync local SQLite pipeline data to Turso (managed SQLite for Vercel).
Runs after each pipeline execution to keep the dashboard data fresh.

Usage:
    python scripts/sync_turso.py
"""

import os
import sys
import sqlite3
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def sync_to_turso():
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")

    if not turso_url or not turso_token:
        logger.warning("TURSO_DATABASE_URL or TURSO_AUTH_TOKEN not set, skipping sync")
        return False

    try:
        from libsql_client import create_client
    except ImportError:
        logger.error("libsql not installed. Run: pip install libsql-client")
        return False

    db_path = os.getenv("DATABASE_PATH", "news_pipeline.db")
    if not Path(db_path).exists():
        logger.error(f"Database not found: {db_path}")
        return False

    # Connect to Turso
    try:
        remote = create_client(url=turso_url, auth_token=turso_token)
        logger.info(f"Connected to Turso: {turso_url[:50]}...")
    except Exception as e:
        logger.error(f"Turso connection failed: {e}")
        return False

    # Create tables in Turso (idempotent)
    remote.execute("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT,
            started_at TEXT,
            completed_at TEXT,
            status TEXT,
            articles_collected INTEGER,
            scripts_generated INTEGER,
            videos_produced INTEGER,
            videos_uploaded INTEGER,
            errors TEXT,
            duration_seconds REAL
        )
    """)

    remote.execute("""
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT,
            youtube_video_id TEXT,
            youtube_url TEXT,
            title TEXT,
            description TEXT,
            tags TEXT,
            category TEXT,
            privacy_status TEXT DEFAULT 'public',
            uploaded_at TEXT,
            upload_status TEXT DEFAULT 'pending'
        )
    """)

    remote.execute("""
        CREATE TABLE IF NOT EXISTS used_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_url TEXT UNIQUE,
            article_title TEXT,
            used_at TEXT,
            video_path TEXT,
            youtube_video_id TEXT
        )
    """)

    remote.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            upload_id TEXT,
            views INTEGER DEFAULT 0,
            watch_time_seconds REAL DEFAULT 0,
            average_view_duration REAL DEFAULT 0,
            click_through_rate REAL DEFAULT 0,
            subscriber_growth INTEGER DEFAULT 0,
            likes INTEGER DEFAULT 0,
            comments INTEGER DEFAULT 0,
            shares INTEGER DEFAULT 0,
            collected_at TEXT
        )
    """)

    remote.execute("""
        CREATE TABLE IF NOT EXISTS learning_insights (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight_type TEXT,
            insight_data TEXT,
            confidence REAL,
            applied INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)

    # Create indexes for dashboard query performance
    remote.execute("CREATE INDEX IF NOT EXISTS idx_runs_started ON pipeline_runs(started_at)")
    remote.execute("CREATE INDEX IF NOT EXISTS idx_uploads_uploaded ON uploads(uploaded_at)")
    remote.execute("CREATE INDEX IF NOT EXISTS idx_articles_used ON used_articles(used_at)")

    # Sync data from local SQLite
    local = sqlite3.connect(db_path)
    local.row_factory = sqlite3.Row

    tables_to_sync = ["pipeline_runs", "uploads", "used_articles", "analytics", "learning_insights"]

    # Use transaction for atomic sync — if anything fails, Turso stays untouched
    try:
        remote.execute("BEGIN TRANSACTION")
        for table in tables_to_sync:
            rows = local.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue

            cols = [d[0] for d in local.execute(f"SELECT * FROM {table} LIMIT 0").description]
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)

            remote.execute(f"DELETE FROM {table}")
            for row in rows:
                remote.execute(
                    f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})",
                    list(row),
                )

            logger.info(f"Synced {len(rows)} rows to {table}")
        remote.execute("COMMIT")
    except Exception as e:
        remote.execute("ROLLBACK")
        logger.error(f"Sync failed (rolled back): {e}")
        local.close()
        return False
    local.close()

    logger.info("Turso sync complete")
    return True


if __name__ == "__main__":
    sync_to_turso()
