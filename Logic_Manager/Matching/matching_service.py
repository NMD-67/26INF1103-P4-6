# Orchestrates loading users, scoring each candidate, and saving the results through the match service.

import logging

from AI_Manager.Profile_Matching.compatibility_scorer import CompatibilityScorer
from Data_Manager.user_source import UserSource

logger = logging.getLogger(__name__)

from dataclasses import replace
from Logic_Manager.Matching.score_calculator import ScoreCalculator
from ...Logic_Manager.Matching.score_calculator import ScoreCalculator

class MatchingService:
    """Orchestrates: load users -> score each -> save. Depends on abstractions only."""

    def __init__(self, scorer: CompatibilityScorer, users: UserSource, match_service, calculator: ScoreCalculator | None = None):
        self._scorer = scorer
        self._users = users
        self._match_service = match_service
        self._calculator = calculator or ScoreCalculator()

    def recommend(self, student_id: str, limit: int | None = None) -> dict:
        main = self._users.get_user(student_id)
        if main is None:
            logger.error("User %s not found", student_id)
            return {}
        decisions = self._match_service.get_decided_candidate_ids(student_id)
        if not decisions.success:
            raise RuntimeError("Could not read previous matching decisions")
        excluded = {str(value) for value in decisions.data}
        excluded.add(str(student_id))
        candidates = self._users.get_candidates(student_id, exclude=excluded)
        if limit:
            candidates = candidates[:limit]

        results = {}
        for c in candidates:
            result = self._scorer.score(main, c)
            if result is not None:
                overall = self._calculator.overall(result.categories)
                results[str(c.student_id)] = replace(result, overall=overall)
        return dict(sorted(results.items(), key=lambda kv: kv[1].overall, reverse=True))

    def save(self, student_id: str, results: dict) -> dict:
        counts = {"saved": 0, "not_saved": 0, "failed": 0}
        for cid, r in results.items():
            try:
                out = self._match_service.create_match(
                    student_id=student_id,
                    candidate_id=cid,
                    compatibility_score=r.overall,
                    interest_score=r.categories.interests_lifestyle,
                    personality_score=r.categories.personality_values,
                    preferences_score=r.categories.relationship_goals,
                    reason=r.reason
                )
            except Exception:
                logger.exception("create_match crashed for %s", cid)
                counts["failed"] += 1
                continue
            counts["saved" if out.success else "not_saved"] += 1
        return counts