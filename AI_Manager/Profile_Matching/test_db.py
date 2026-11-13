# test_db.py (project root)
import os
from pathlib import Path
from dotenv import load_dotenv
import psycopg

# test_db.py is in AI_Manager/Profile_Matching/, so the root is 3 levels up
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
url = os.environ["SUPABASE_URL"]
print("Starts with:", url.split("://")[0])   # prints the scheme only, not the password

with psycopg.connect(url, sslmode="require", connect_timeout=10) as conn:
    print(conn.execute("SELECT 1").fetchone())