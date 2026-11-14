"""Create and verify a PostgreSQL pool without connecting during import."""
import logging
import os
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

logger = logging.getLogger(__name__)


class DatabaseConnection:
    def __init__(self, database_url=None, timeout=10):
        self._database_url = database_url
        self._timeout = timeout

    def create_pool(self):
        database_url = self._database_url or os.getenv("SUPABASE_URL")
        if not database_url or not database_url.strip():
            raise RuntimeError("SUPABASE_URL is missing")
        pool = ConnectionPool(
            conninfo=database_url, min_size=1, max_size=5, open=False,
            kwargs={"sslmode": "require", "row_factory": dict_row,
                    "connect_timeout": self._timeout},
        )
        try:
            pool.open()
            pool.wait(timeout=self._timeout)
            with pool.connection() as conn:
                conn.execute("SELECT 1")
        except Exception:
            logger.exception("Error occurred while creating connection pool")
            pool.close()
            raise
        logger.info("Connected to database")
        return pool
