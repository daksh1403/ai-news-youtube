import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger(__name__)


def init_db(db_path: str = "news_pipeline.db"):
    schema_path = Path(__file__).parent / "schema.sql"
    try:
        conn = sqlite3.connect(db_path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=10000")
        conn.execute("PRAGMA synchronous=NORMAL")
        schema = schema_path.read_text()
        conn.executescript(schema)
        conn.close()
        logger.info(f"Database initialized: {db_path} (WAL mode)")
    except Exception as e:
        logger.error(f"Database init failed: {e}")
        raise


@contextmanager
def get_db(db_path: str = "news_pipeline.db"):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def get_db_connection(db_path: str = "news_pipeline.db"):
    conn = sqlite3.connect(db_path, timeout=30)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.row_factory = sqlite3.Row
    return conn
