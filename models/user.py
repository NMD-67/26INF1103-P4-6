from dataclasses import dataclass

@dataclass
class User:
  student_id: str
  name: str
  birthday: int
  gender: str
  year: int
  course: str
  bio: str
  religion: str
  race: str
  mbti: str
  match_preference: str
  here_for: str
  expectations: str
  ccas: list[str]
  events: list[str]
  hobbies: list[str]
  interest_groups: list[str]
  deal_breakers: list[dict]
  __tele_handle: str

  @property
  def student_id(self):
    return self.student_id

  def get_user_details(self):
    user_obj = {}
    for attr, value in vars(self).items():
      if attr.startswith("__"):
        continue
      user_obj[attr] = value
    return user_obj

@dataclass
class Candidate(User):
  __compatability_score: int
  __reason: str

  def get_user_details(self) -> dict:
    return super().get_user_details().update({"compatability_score": self.__compatability_score, "reason": self.__reason})

  def handle_decision(self, accepted=False):
    pass

@dataclass
class Match(User):
  recco_list: list[str]
  def generate_reccos(self):
    pass

  def get_user_details(self):
    return super().get_user_details().update({"tele_handle": self.__tele_handle})

class Profile(User):
  def get_user_details(self):
    return super().get_user_details().update({"tele_handle": self.__tele_handle})

  