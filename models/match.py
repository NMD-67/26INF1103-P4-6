from dataclasses import dataclass
from models.user import User


@dataclass
class Match(User):
    recco_list: list[str] = None

    def get_user_details(self):
        return super().get_user_details()
