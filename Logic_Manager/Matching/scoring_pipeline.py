"""Shared AI scoring, weighted calculation and persistence for matching workflows."""
from dataclasses import replace
from AI_Manager.Profile_Matching.AI_Validator_Workflow.review_service import ReviewService
import logging
from Logic_Manager.Matching.score_calculator import ScoreCalculator

logger = logging.getLogger(__name__)


class ScoringPipeline:
    def __init__(self, scorer, matches, calculator=None, reviewer=None, reviewer_factory=None):
        self._scorer = scorer
        self._matches = matches
        self._calculator = calculator if calculator is not None else ScoreCalculator()
        self._reviewer = reviewer
        self._reviewer_factory = reviewer_factory

    def score_candidates(self, viewer, candidates):
        scored = []
        for candidate in candidates:
            result = self._scorer.score(viewer, candidate)
            if result is not None:
                ReviewService.validate_scores([result.categories], 1)
                scored.append((candidate, result))
        if not scored:
            return {}
        # Load the local model only when matching is requested, once per pipeline.
        if self._reviewer is None and self._reviewer_factory is not None:
            self._reviewer = self._reviewer_factory()
        if self._reviewer is not None:
            try:
                validated = list(self._reviewer.correct(viewer,
                    [candidate for candidate, _ in scored],
                    [result.categories for _, result in scored]))
                ReviewService.validate_scores(validated, len(scored))
                scored = [(candidate, replace(result, categories=categories))
                          for (candidate, result), categories in zip(scored, validated)]
            except Exception:
                logger.exception("Score review failed; retaining validated AI scores")
        results = {str(candidate.student_id): replace(result,
            overall=self._calculator.overall(result.categories))
            for candidate, result in scored}
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
