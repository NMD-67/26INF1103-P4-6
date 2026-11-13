# Immutable value object holding one compatibility score and its short reason.

from dataclasses import dataclass

@dataclass(frozen=True)
class ScoreResult:
    """Immutable result of scoring one pair."""
    score: int
    reason: str | None = None