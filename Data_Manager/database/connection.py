import os
import logging
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(dotenv_path=Path(__file__).parent.parent.parent / ".env")

database_url = os.environ["SUPABASE_URL"]

def create_connection_pool() -> ConnectionPool:
  """Create and verify the connection pool to PostgreSQL"""
  if not database_url:
    raise RuntimeError(
      "SUPABASE_URL is missing"
    )

  pool = ConnectionPool(
    conninfo=database_url,
    min_size=1,
    max_size=5,
    open=False,
    kwargs={"sslmode": "require"}
  )

  try:
    pool.open()

    pool.wait(timeout=10)

    with pool.connection() as conn:
      conn.execute("SELECT 1")

    print("Connected to Database")

    return pool
  except Exception as e:
    logging.error(f"Error occurred while creating connection pool: {e}")
    pool.close()
    raise