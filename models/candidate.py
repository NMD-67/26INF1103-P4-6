from dataclasses import dataclass

from models.user import User

@dataclass(kw_only=True)
class Candidate(User):
  compatibility_score: int
  reason: str = None
  interst_score: int = None
  personality_score: int = None
  preferences_score: int = None

  def get_user_details(self) -> dict:
    super().get_user_details().update({"compatibility_score": self.compatibility_score, "reason": self.reason})
    return super().get_user_details()