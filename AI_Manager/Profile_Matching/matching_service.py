import os
import logging
from dotenv import load_dotenv
from supabase import create_client

from models.user import User
from models.match import Match
from AI_Manager.Profile_Matching.scoring import (
    get_groq_client, get_compatibility_score, to_user
)

load_dotenv()
logger = logging.getLogger(__name__)

USERS_TABLE = "users"

def get_supabase():
    url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_API_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_API_KEY in .env")


def fetch_user(supabase, student_id) -> User | None:
    res = (supabase.table(USERS_TABLE).select("*")
           .eq("student_id", str(student_id)).execute())
    return to_user(res.data[0]) if res.data else None


def get_rejected_ids(supabase, student_id) -> set:
    # TODO: replace with your real rejected-matches lookup in Supabase.
    return set()


def fetch_candidates(supabase, main_id, exclude_ids, limit=None) -> list[User]:
    query = (supabase.table(USERS_TABLE).select("*")
             .neq("student_id", str(main_id)).order("student_id"))
    if limit:
        query = query.limit(limit)
    rows = query.execute().data or []

    candidates = []
    for row in rows:
        sid = row.get("student_id")
        if sid is None or str(sid) in exclude_ids:
            continue
        try:
            candidates.append(to_user(row))
        except Exception:
            logger.warning("Skipping unreadable row %s", sid)
    return candidates


def generate_recommendations(supabase, groq_client, student_id, limit=None) -> Match | None:
    """Returns a Match whose recco_list is {candidate_id: score}, best first."""
    main_user = fetch_user(supabase, student_id)
    if main_user is None:
        logger.error("User %s not found", student_id)
        return None

    exclude = get_rejected_ids(supabase, student_id)
    candidates = fetch_candidates(supabase, student_id, exclude, limit)

    scores = {}
    for c in candidates:
        score = get_compatibility_score(groq_client, main_user, c)
        if score is not None:
            scores[str(c.student_id)] = score

    ranked = dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True))
    return Match.from_dict({**main_user.get_user_details(), "recco_list": ranked})


def save_recco_list(supabase, student_id, recco_list: dict):
    # ASSUMPTION: users table has a jsonb column called "recco_student_id".
    res = (supabase.table(USERS_TABLE).select("recco_student_id")
           .eq("student_id", str(student_id)).execute())
    existing = (res.data[0].get("recco_student_id") if res.data else None) or {}
    merged = {**existing, **recco_list} if isinstance(existing, dict) else recco_list
    supabase.table(USERS_TABLE).update({"recco_student_id": merged}) \
        .eq("student_id", str(student_id)).execute()

# Adjust these two imports to wherever your service and Result classes live
from results.success import Success
from services.match_service import MatchService
from results.error import Error

def save_matches(match_service, student_id, scores: dict, reasons: dict | None = None) -> dict:
    """Saves {candidate_id: score} through create_match. Never raises."""
    counts = {"saved": 0, "not_saved": 0, "failed": 0}

    for candidate_id, score in scores.items():
        reason = reasons.get(candidate_id) if reasons else None
        try:
            result = match_service.create_match(
                str(student_id), str(candidate_id), float(score), reason
            )
        except Exception:
            logger.exception("create_match crashed for %s -> %s", student_id, candidate_id)
            counts["failed"] += 1
            continue

        if isinstance(result, Success):
            counts["saved"] += 1
        else:
            # create_match returns Error("Match already exists") when it returns False
            logger.info("Not saved %s -> %s: %s", student_id, candidate_id,
                        getattr(result, "error_msg", result))
            counts["not_saved"] += 1

    return counts

from Data_Manager.database.connection import create_connection_pool   # adjust to the real path
from repositories.matches_repo import MatchesRepo
from services.match_service import MatchService

if __name__ == "__main__":
    supabase = get_supabase()
    client = get_groq_client()
    pool = create_connection_pool()
    try:
        match = generate_recommendations(supabase, client, "2605770", limit=5)
        if match:
            print(match.recco_list)
            match_service = MatchService(MatchesRepo(pool))
            print(save_matches(match_service, match.student_id, match.recco_list))
    finally:
        client.close()
        pool.close()