# Immutable value object holding one compatibility score and its short reason.

from dataclasses import dataclass

from .category_scores import CategoryScores

@dataclass(frozen=True)
class ScoreResult:
    """AI output for one pair. `overall` is filled in by ScoreCalculator, not the AI."""
    categories: CategoryScores
    reason: str | None = None
    overall: int | None = None