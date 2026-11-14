"""Deterministic MBTI TYPE SIMILARITY, not a scientifically proven match score."""
from .category_validator import CategoryValidator


class MbtiTableValidator(CategoryValidator):
    category = "personality_values"
    _OPTIONS = ("EI", "SN", "TF", "JP")

    def validate_batch(self, main_user, candidates):
        a = self._clean(getattr(main_user, "mbti", None))
        result = []
        for candidate in candidates:
            b = self._clean(getattr(candidate, "mbti", None))
            if a is None or b is None:
                result.append(None)
            else:
                shared = sum(x == y for x, y in zip(a, b))
                result.append(40 + 15 * shared)  # 40,55,70,85,100
        return result

    @classmethod
    def _clean(cls, value):
        text = str(value or "").strip().upper()
        return text if len(text) == 4 and all(
            letter in pair for letter, pair in zip(text, cls._OPTIONS)
        ) else None
