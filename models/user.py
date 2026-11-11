from dataclasses import dataclass, fields, field
from models.dealbreaker import DealBreaker


@dataclass(kw_only=True)
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
    ccas: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)
    hobbies: list[str] = field(default_factory=list)
    interest_groups: list[str] = field(default_factory=list)
    tele_handle: str = None
    insta_handle: str = None

    @classmethod
    def from_dict(cls, data: dict):
        data = data.copy()
        if "interests" in data and "interest_groups" not in data:
            data["interest_groups"] = data["interests"]
        class_fields = {field.name for field in fields(cls)}
        return cls(**{key: value for key, value in data.items() if key in class_fields})

    def get_user_details(self) -> dict:
        user_obj = {}
        for attr, value in vars(self).items():
            if attr.startswith("__"):
                continue
            user_obj[attr] = value
        return user_obj

    def print_user_details(self) -> None:
        user_obj = self.get_user_details()
        for attr, value in user_obj.items():
            print(f"{attr}: {value}")
