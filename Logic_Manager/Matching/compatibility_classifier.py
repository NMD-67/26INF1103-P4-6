"""Project-defined classification based on multiple validated AI fields."""
import math


class CompatibilityClassifier:
    STRONG_THRESHOLD = 70
    MODERATE_THRESHOLD = 50

    def classify(self, scores):
        interests = scores.get("interest_score")
        personality = scores.get("personality_score")
        goals = scores.get("preferences_score")
        for value in (interests, personality, goals):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 100):
                return "Not available"

        if (interests >= self.STRONG_THRESHOLD
                and personality >= self.STRONG_THRESHOLD
                and goals >= self.STRONG_THRESHOLD):
            return "Strong compatibility"
        if (interests >= self.MODERATE_THRESHOLD
                and personality >= self.MODERATE_THRESHOLD
                and goals >= self.MODERATE_THRESHOLD):
            return "Moderate compatibility"
        return "Low compatibility"
