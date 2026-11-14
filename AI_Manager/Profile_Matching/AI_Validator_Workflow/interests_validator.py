from models.user import User
from .category_validator import CategoryValidator
from .sentence_similarity import SentenceSimilarity


class InterestsValidator(CategoryValidator):
    category = "interests_lifestyle"
    FIELDS = ("hobbies", "ccas", "events", "interest_groups")

    def __init__(self, similarity: SentenceSimilarity):
        self._similarity = similarity          # aggregation: injected, shared

    def validate_batch(self, main_user, candidates):
        return self._similarity.compare_many(
            self._text(main_user), [self._text(c) for c in candidates])

    def _text(self, user: User) -> str:
        parts = []
        for f in self.FIELDS:
            parts.extend(str(x) for x in (getattr(user, f, None) or []))
        return ", ".join(parts)