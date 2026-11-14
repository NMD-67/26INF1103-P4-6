# Orchestrates loading users, scoring each candidate, and saving the results through the match service.

import logging

from AI_Manager.Profile_Matching.compatibility_scorer import CompatibilityScorer
from Data_Manager.user_source import UserSource

logger = logging.getLogger(__name__)

from Logic_Manager.Matching.score_calculator import ScoreCalculator
from Logic_Manager.Matching.scoring_pipeline import ScoringPipeline

class MatchingService:
    """Orchestrates: load users -> score each -> save. Depends on abstractions only."""

    def __init__(self, scorer: CompatibilityScorer, users: UserSource, match_service, calculator: ScoreCalculator | None = None):
        self._scorer = scorer
        self._users = users
        self._match_service = match_service
        self._pipeline = ScoringPipeline(scorer, match_service, calculator)

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
        if limit is not None:
            candidates = candidates[:limit]

        return self._pipeline.score_candidates(main, candidates)

    def save(self, student_id: str, results: dict) -> dict:
        return self._pipeline.save_results(student_id, results)
