from models.user import User
from models.dealbreaker import DealBreaker
from dataclasses import dataclass, field


@dataclass(kw_only=True)
class Profile(User):
    dealbreakers: DealBreaker | dict | None = field(default=None, repr=None)

    def __post_init__(self):
        if isinstance(self.dealbreakers, dict):
            self.dealbreakers = DealBreaker(**self.dealbreakers)

    def get_user_details(self) -> dict:
        super().get_user_details().update(
            {"dealbreakers": self.dealbreakers, "tele_handle": self.tele_handle}
        )
        return super().get_user_details()
