"""Shared AI scoring, weighted calculation and persistence for matching workflows."""
from dataclasses import replace
import logging
from Logic_Manager.Matching.score_calculator import ScoreCalculator

logger = logging.getLogger(__name__)


class ScoringPipeline:
    def __init__(self, scorer, matches, calculator=None):
        self._scorer = scorer
        self._matches = matches
        self._calculator = calculator if calculator is not None else ScoreCalculator()

    def score_candidates(self, viewer, candidates):
        results = {}
        for candidate in candidates:
            result = self._scorer.score(viewer, candidate)
            if result is not None:
                results[str(candidate.student_id)] = replace(
                    result, overall=self._calculator.overall(result.categories))
        return dict(sorted(results.items(), key=lambda item: item[1].overall, reverse=True))

    def save_results(self, student_id, results):
        counts = {"saved": 0, "not_saved": 0, "failed": 0}
        for candidate_id, result in results.items():
            try:
                categories = result.categories
                saved = self._matches.create_match(
                    student_id=student_id, candidate_id=candidate_id,
                    compatibility_score=result.overall,
                    interest_score=categories.interests_lifestyle,
                    personality_score=categories.personality_values,
                    preferences_score=categories.relationship_goals,
                    reason=result.reason)
                counts["saved" if saved.success else "not_saved"] += 1
            except Exception:
                logger.exception("Could not save recommendation for %s", candidate_id)
                counts["failed"] += 1
        return counts
