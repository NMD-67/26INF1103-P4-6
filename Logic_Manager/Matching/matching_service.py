
"""Profile matching orchestration and persistence."""

import logging
from dataclasses import replace

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
        self._reviewer = reviewer

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

        # Step 1: Generate initial scores
        scored = []

        for candidate in candidates:
            result = self._scorer.score(
                main_user,
                candidate
            )

            if result is not None:
                scored.append((candidate, result))

        # Step 2: Validate category scores
        if self._reviewer and scored:

            validated = self._reviewer.correct(
                main_user,
                [c for c, _ in scored],
                [r.categories for _, r in scored]
            )

            scored = [
                (
                    candidate,
                    replace(result, categories=categories)
                )
                for (candidate, result), categories
                in zip(scored, validated)
            ]

        # Step 3: Recalculate overall scores
        results = {}

        for candidate, result in scored:

            overall = self._calculator.overall(
                result.categories
            )

            results[str(candidate.student_id)] = replace(
                result,
                overall=overall
            )

        # Step 4: Rank candidates
        return dict(
            sorted(
                results.items(),
                key=lambda item: item[1].overall,
                reverse=True
            )
        )

    def save(self, student_id, results):

        counts = {
            "saved": 0,
            "not_saved": 0,
            "failed": 0
        }

        for candidate_id, result in results.items():

            try:
                outcome = self._match_service.create_match(
                    student_id=student_id,
                    candidate_id=candidate_id,
                    compatibility_score=result.overall,
                    interest_score=(
                        result.categories.interests_lifestyle
                    ),
                    personality_score=(
                        result.categories.personality_values
                    ),
                    preferences_score=(
                        result.categories.relationship_goals
                    ),
                    reason=result.reason
                )

                if outcome.success:
                    counts["saved"] += 1
                else:
                    counts["not_saved"] += 1

            except Exception:
                logger.exception(
                    "Failed to save candidate %s",
                    candidate_id
                )
                counts["failed"] += 1

        return counts
