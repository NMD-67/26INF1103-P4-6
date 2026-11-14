from AI_Manager.Profile_Matching.category_scores import CategoryScores
from models.category_scores import CategoryScores

class ScoreCalculator:
    """Combines the three category scores into the overall score."""

    WEIGHTS = {
        "interests_lifestyle": 0.40,
        "personality_values": 0.30,
        "relationship_goals": 0.30,
    }

    def overall(self, c: CategoryScores) -> int:
        total = (c.interests_lifestyle * self.WEIGHTS["interests_lifestyle"]
                 + c.personality_values * self.WEIGHTS["personality_values"]
                 + c.relationship_goals * self.WEIGHTS["relationship_goals"])
        return int(round(total))