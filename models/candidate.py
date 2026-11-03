from dataclasses import dataclass

from models.user import User

@dataclass
class Candidate(User):
  __compatability_score: int
  __reason: str

  def get_user_details(self) -> dict:
    return super().get_user_details().update({"compatability_score": self.__compatability_score, "reason": self.__reason})

  def handle_decision(self, accepted=False):
    pass