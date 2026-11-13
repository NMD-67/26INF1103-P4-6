# ScoreResult (value object)

from dataclasses import dataclass

@dataclass(frozen=True)
class ScoreResult:
    """Immutable result of scoring one pair."""
    score: int
    reason: str | None = None