from abc import ABC, abstractmethod

from models.user import User
from .score_result import ScoreResult

class CompatibilityScorer(ABC):
    @abstractmethod
    def score(self, main_user: User, candidate: User) -> ScoreResult | None:
        """Return a ScoreResult, or None if scoring failed. Never raises."""