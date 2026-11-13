"""Two-way eligibility rules applied before any AI compatibility scoring.

Race and religion selections in SITogether's form are *blacklists*, not
required inclusions.  This class does not query the database or call AI.
"""

from collections.abc import Mapping


class MutualPreferenceFilter:
    _NO_PREFERENCE = {"", "both", "no preference", "prefer not to say", "any"}

    @staticmethod
    def _text(value) -> str:
        return str(value).strip().casefold() if value is not None else ""

    @classmethod
    def _preferences(cls, prefs) -> dict:
        if prefs is None:
            return {}
        if isinstance(prefs, Mapping):
            return dict(prefs)
        # Accept the existing DealBreaker dataclass as well.
        return {
            key: getattr(prefs, key, None)
            for key in ("gender", "min_age", "max_age", "religion", "race")
        }

    @classmethod
    def _blocked(cls, value, blacklist) -> bool:
        if not blacklist:
            return False
        if isinstance(blacklist, str):
            blacklist = [blacklist]
        prohibited = {
            cls._text(item)
            for item in blacklist
            if cls._text(item) not in cls._NO_PREFERENCE
        }
        # A non-disclosed category is not inferred from other user details.
        return cls._text(value) in prohibited

    @classmethod
    def meets_preferences(cls, owner, candidate, preferences=None) -> bool:
        """Whether candidate satisfies owner's selected matching restrictions."""
        prefs = cls._preferences(preferences)
        wanted_gender = cls._text(prefs.get("gender") or owner.match_preference)
        if wanted_gender not in cls._NO_PREFERENCE:
            if cls._text(candidate.gender) != wanted_gender:
                return False

        low, high = prefs.get("min_age"), prefs.get("max_age")
        if low is not None or high is not None:
            try:
                age = int(candidate.age)
            except (TypeError, ValueError):
                return False
            if (low is not None and age < int(low)) or (
                high is not None and age > int(high)
            ):
                return False

        if cls._blocked(candidate.religion, prefs.get("religion")):
            return False
        if cls._blocked(candidate.race, prefs.get("race")):
            return False
        return True

    def is_eligible(self, student, candidate, student_prefs=None, candidate_prefs=None) -> bool:
        """Both students must accept one another's attributes and restrictions."""
        if str(student.student_id) == str(candidate.student_id):
            return False
        return (
            self.meets_preferences(student, candidate, student_prefs)
            and self.meets_preferences(candidate, student, candidate_prefs)
        )
