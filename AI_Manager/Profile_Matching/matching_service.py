# Orchestrates loading users, scoring each candidate, and saving the results through the match service.

import logging
logger = logging.getLogger(__name__)

from .compatibility_scorer import CompatibilityScorer
from .user_source import UserSource

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