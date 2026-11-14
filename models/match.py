from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from models.user import User

if TYPE_CHECKING:
    from AI_Manager.Suggestions_generator.suggestions_generator import SuggestionsGenerator


@dataclass
class Match(User):
    """A mutually matched student's profile, including AI recommendations."""

    ai_suggestions: list[str] = field(default_factory=list)
    compatibility_score: int | None = None
    interest_score: int | None = None
    personality_score: int | None = None
    preferences_score: int | None = None
    reason: str | None = None

    def generate_reccos(
        self,
        viewing_user: User,
        ai_manager: "SuggestionsGenerator",
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
            self.ai_suggestions = []
            return result

        # The AI returns three lists; the Match model stores one list[str].
        self.ai_suggestions = [
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
