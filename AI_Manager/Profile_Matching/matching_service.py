# scorer + repo + logic, orchestrates only

import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client

from Data_Manager.database.connection import create_connection_pool
from repositories.matches_repo import MatchesRepo
from services.match_service import MatchService
from .scoring import GroqScorer, get_groq_client
from .candidate_loader import SupabaseUserSource

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

import logging
from .scoring import CompatibilityScorer
from .candidate_loader import UserSource

logger = logging.getLogger(__name__)


class MatchingService:
    """Orchestrates: load users -> score each -> save. Depends on abstractions only."""

    def __init__(self, scorer: CompatibilityScorer, users: UserSource, match_service):
        self._scorer = scorer              # association/aggregation: injected, not owned
        self._users = users
        self._match_service = match_service

    def recommend(self, student_id: str, limit: int | None = None) -> dict:
        main = self._users.get_user(student_id)
        if main is None:
            logger.error("User %s not found", student_id)
            return {}
        candidates = self._users.get_candidates(student_id, exclude=set())
        if limit:
            candidates = candidates[:limit]

        results = {}
        for c in candidates:
            result = self._scorer.score(main, c)     # polymorphic call
            if result is not None:
                results[str(c.student_id)] = result
        return dict(sorted(results.items(), key=lambda kv: kv[1].score, reverse=True))

    def save(self, student_id: str, results: dict) -> dict:
        counts = {"saved": 0, "not_saved": 0, "failed": 0}
        for cid, r in results.items():
            try:
                out = self._match_service.create_match(
                    str(student_id), cid, float(r.score), r.reason)
            except Exception:
                logger.exception("create_match crashed for %s", cid)
                counts["failed"] += 1
                continue
            counts["saved" if out.success else "not_saved"] += 1
        return counts
    
def get_supabase():
    url, key = os.getenv("SUPABASE_API_URL"), os.getenv("SUPABASE_API_KEY")
    if not url or not key:
        raise RuntimeError("Set SUPABASE_API_URL and SUPABASE_API_KEY in .env")
    return create_client(url, key)

# Test
if __name__ == "__main__":
    client = get_groq_client()
    pool = create_connection_pool()
    try:
        service = MatchingService(
            GroqScorer(client),
            SupabaseUserSource(get_supabase()),
            MatchService(MatchesRepo(pool)),
        )
        results = service.recommend("2605770", limit=5)
        for cid, r in results.items():
            print(cid, r.score, r.reason)
        print(service.save("2605779", results))
    finally:
        client.close()
        pool.close()