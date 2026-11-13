import os
from dotenv import load_dotenv
from supabase import create_client

from AI_Manager.Profile_Matching.scoring import (
    get_groq_client, get_compatibility_score, to_user
)

load_dotenv()

USERS_TABLE = "users"   # change if your table is named differently
MAIN_USER_ID = "2605770"
MAX_CANDIDATES = 3      # keep small while testing to save API calls


def get_supabase():
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_API_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in .env")
    return create_client(url, key)


if __name__ == "__main__":
    supabase = get_supabase()

    # Main user
    res = supabase.table(USERS_TABLE).select("*").eq("student_id", MAIN_USER_ID).execute()
    if not res.data:
        raise SystemExit(f"User {MAIN_USER_ID} not found (or blocked by RLS)")
    main_user = to_user(res.data[0])
    print("Main user:", main_user)

    # Candidates (everyone else)
    res = (supabase.table(USERS_TABLE).select("*")
           .neq("student_id", MAIN_USER_ID).limit(MAX_CANDIDATES).execute())
    candidates = [to_user(row) for row in res.data]
    print(f"Fetched {len(candidates)} candidates")

    client = get_groq_client()
    for c in candidates:
        print(c.student_id, c.name, "->", get_compatibility_score(client, main_user, c))
    client.close()