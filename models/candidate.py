from dataclasses import dataclass

from models.user import User

@dataclass(kw_only=True)
class Candidate(User):
  compatibility_score: int
  reason: str = None
  interest_score: int = None
  personality_score: int = None
  preferences_score: int = None
