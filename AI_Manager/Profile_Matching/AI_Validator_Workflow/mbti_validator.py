from .category_validator import CategoryValidator


class MbtiTableValidator(CategoryValidator):
    """Rule-based MBTI check: more shared letters, higher score. Placeholder heuristic;
    swap for an EQIQs-backed validator without touching any other class."""
    category = "personality_values"

    def validate_batch(self, main_user, candidates):
        a = self._clean(main_user.mbti)
        out = []
        for c in candidates:
            b = self._clean(c.mbti)
            out.append(None if a is None or b is None
                       else 20 + 20 * sum(x == y for x, y in zip(a, b)))
        return out

    @staticmethod
    def _clean(value):
        v = (value or "").strip().upper()
        return v if len(v) == 4 and v.isalpha() else None