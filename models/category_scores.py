from dataclasses import dataclass

@dataclass(frozen=True)
class CategoryScores:
    interests_lifestyle: int
    personality_values: int
    relationship_goals: int