
"""Profile matching orchestration and persistence."""

import logging
from Logic_Manager.Matching.scoring_pipeline import ScoringPipeline

from AI_Manager.Profile_Matching.compatibility_scorer import CompatibilityScorer
from Data_Manager.user_source import UserSource
from Logic_Manager.Matching.score_calculator import ScoreCalculator

logger = logging.getLogger(__name__)


class MatchingService:

    def __init__(
        self,
        scorer: CompatibilityScorer,
        users: UserSource,
        match_service,
        calculator: ScoreCalculator | None = None,
        reviewer=None
    ):
        self._scorer = scorer
        self._users = users
        self._match_service = match_service
        self._calculator = calculator or ScoreCalculator()
        self._pipeline = ScoringPipeline(scorer, match_service, self._calculator, reviewer=reviewer)

    def recommend(self, student_id, limit=None):

        main_user = self._users.get_user(student_id)

        if main_user is None:
            logger.error("User %s not found", student_id)
            return {}

        decisions = (
            self._match_service.get_decided_candidate_ids(
                student_id
            )
        )

        if not decisions.success:
            raise RuntimeError(
                "Could not retrieve previous matching decisions"
            )

        excluded = {
            str(value) for value in decisions.data
        }
        excluded.add(str(student_id))

        candidates = self._users.get_candidates(
            student_id,
            exclude=excluded
        )

        if limit is not None:
            if limit < 0:
                raise ValueError("Limit cannot be negative")

            candidates = candidates[:limit]

        return self._pipeline.score_candidates(main_user, candidates)

    def save(self, student_id, results):
        return self._pipeline.save_results(student_id, results)
