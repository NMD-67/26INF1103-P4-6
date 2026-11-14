from .category_validator import CategoryValidator
from .sentence_similarity import SentenceSimilarity


class GoalsValidator(CategoryValidator):
    """Hard preference check first, then text similarity of here_for + expectations."""
    category = "relationship_goals"
    _NO_PREFERENCE = {"", "any", "all", "both", "everyone", "no preference"}

    def __init__(self, similarity: SentenceSimilarity):
        self._similarity = similarity

    def validate_batch(self, main_user, candidates):
        results = [None] * len(candidates)
        fitting = []
        for i, c in enumerate(candidates):
            if (self._fits(main_user.match_preference, c.gender)
                    and self._fits(c.match_preference, main_user.gender)):
                fitting.append(i)
            else:
                results[i] = 10                    # preferences clash: no API call needed
        sims = self._similarity.compare_many(
            self._text(main_user), [self._text(candidates[i]) for i in fitting])
        for i, sim in zip(fitting, sims):
            results[i] = sim
        return results

    def _fits(self, preference, gender) -> bool:
        pref = (preference or "").strip().lower()
        g = (gender or "").strip().lower()
        return pref in self._NO_PREFERENCE or not g or pref == g

    @staticmethod
    def _text(user) -> str:
        return f"{user.here_for or ''}. {user.expectations or ''}".strip(" .")