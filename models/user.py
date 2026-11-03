from dataclasses import dataclass

@dataclass
class User:
  student_id: str
  name: str = None
  birthday: int = None
  gender: str = None
  year: int = None
  course: str = None
  bio: str = None
  religion: str = None
  race: str = None
  mbti: str = None
  match_preference: str = None
  here_for: str = None
  expectations: str = None
  ccas: list[str] = None
  events: list[str] = None
  hobbies: list[str] = None
  interest_groups: list[str] = None
  deal_breakers: list[dict] = None
  __tele_handle: str = None

  def get_user_details(self):
    user_obj = {}
    for attr, value in vars(self).items():
      if attr.startswith("__"):
        continue
      user_obj[attr] = value
    return user_obj


  