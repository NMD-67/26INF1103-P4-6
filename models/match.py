from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.user import User

if TYPE_CHECKING:
    from AI_Manager.matchmaking_ai import MatchmakingAIManager


@dataclass
class Match(User):
    """A mutually matched student's profile, including AI recommendations."""

    recco_list: list[str] = field(default_factory=list)

    def get_user_details(self) -> dict:
        return super().get_user_details()

    def generate_reccos(
        self,
        viewing_user: User,
        ai_manager: "MatchmakingAIManager",
    ) -> dict:
        """Generate recommendations for the viewing user and this match.

        This method stores the suggestions on this Match object in memory.
        The caller must first confirm that the students mutually accepted.
        """
        result = ai_manager.generate_suggestions(
            viewing_user.get_user_details(),
            self.get_user_details(),
        )

        if not result.get("success"):
            self.recco_list = []
            return result

        # The AI returns three lists; the Match model stores one list[str].
        self.recco_list = [
            f"Common interest: {item}"
            for item in result["common_interests"]
        ] + [
            f"Conversation starter: {item}"
            for item in result["conversation_starters"]
        ] + [
            f"Outing idea: {item}"
            for item in result["outing_ideas"]
        ]

        return result
