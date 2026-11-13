# Abstract base class defining the contract that any scorer must provide a score(main_user, candidate) method.
from abc import ABC, abstractmethod

from models.user import User
from .score_result import ScoreResult

class CompatibilityScorer(ABC):
    def prepare(self) -> bool:
        """Ready by default; scorers with deferred resources can override this."""
        return True

    @abstractmethod
    def score(self, main_user: User, candidate: User) -> ScoreResult | None:
        """Return a ScoreResult, or None if scoring failed. Never raises."""