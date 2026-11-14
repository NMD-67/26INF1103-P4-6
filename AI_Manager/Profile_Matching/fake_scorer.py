# Test double that returns a fixed score without calling any API, and can stand in for GroqScorer.

from .category_scores import CategoryScores
from .compatibility_scorer import CompatibilityScorer
from .score_result import ScoreResult


class FakeScorer(CompatibilityScorer):
    def __init__(self, fixed_score=50):
        self._fixed = fixed_score

    def score(self, main_user, candidate):
        c = CategoryScores(self._fixed, self._fixed, self._fixed)
        return ScoreResult(categories=c, reason="fake reason")