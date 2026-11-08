from models.user import User
from models.dealbreaker import DealBreaker
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Profile(User):
    dealbreakers: DealBreaker | None = field(default=None, repr=None)

    def get_user_details(self) -> dict:
        super().get_user_details().update({"dealbreakers": self.dealbreakers})
        return super().get_user_details()
