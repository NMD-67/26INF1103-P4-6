from abc import ABC, abstractmethod

from models.user import User


class CategoryValidator(ABC):
    """Independent check for one AI category. `category` must match a CategoryScores field."""
    category: str

    @abstractmethod
    def validate_batch(self, main_user: User, candidates: list[User]) -> list[int | None]:
        """One 0-100 score per candidate (None = can't be checked), in the same order."""

    def validate(self, main_user: User, candidate: User) -> int | None:
        return self.validate_batch(main_user, [candidate])[0]