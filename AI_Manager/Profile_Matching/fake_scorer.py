# Test double that returns a fixed score without calling any API, and can stand in for GroqScorer.

from .compatibility_scorer import CompatibilityScorer
from .score_result import ScoreResult


class FakeScorer(CompatibilityScorer):
    """Test double, substitutable for GroqScorer (LSP)."""

    def __init__(self, fixed_score=50):
        self._fixed = fixed_score

    def score(self, main_user, candidate):
        return ScoreResult(self._fixed, "fake reason")