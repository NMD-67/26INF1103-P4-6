"""Connect mutual matches to SuggestionsGenerator and ConsoleIO."""

import logging
from dataclasses import asdict, is_dataclass

from AI_Manager.Suggestions_generator.suggestions_generator import SuggestionsGenerator

logger = logging.getLogger(__name__)


class ConnectionSuggestionService:
    """Find mutual matches, generate their suggestions, and return UI results."""

    CONTACT_FIELDS = ("student_id", "name", "tele_handle", "insta_handle")

    def __init__(self, match_service, user_service, suggestions_generator: SuggestionsGenerator):
        self._match_service = match_service
        self._user_service = user_service
        self._generator = suggestions_generator

    @staticmethod
    def _profile_dict(user) -> dict:
        if isinstance(user, dict):
            return user.copy()
        if is_dataclass(user) and not isinstance(user, type):
            return asdict(user)
        if hasattr(user, "get_user_details"):
            details = user.get_user_details()
            if isinstance(details, dict):
                return details
        raise TypeError(f"Unsupported user type: {type(user).__name__}")

    def get_matches_for_user(self, user_id: str) -> list[dict]:
        """Call Match.generate_reccos once for each mutual Match object."""
        user_id = str(user_id).strip()
        try:
            response = self._match_service.get_all_matches(user_id)
            if not response.success:
                raise RuntimeError("Could not retrieve mutual matches")
            matches = response.data
            if not isinstance(matches, (list, tuple)):
                raise TypeError("Unexpected matches format")
        except Exception as error:
            logger.warning("Unable to retrieve mutual matches: %s", type(error).__name__)
            return [{
                "success": False,
                "user_a": user_id,
                "error": "Connections are temporarily unavailable.",
            }]
        if not matches:
            return []

        try:
            viewer_result = self._user_service.get_user(user_id)
        except Exception as error:
            logger.warning("Unable to load viewing user: %s", type(error).__name__)
            viewer_result = None

        output = []
        seen_ids = set()
        for match in matches:
            other_id = str(match.student_id).strip()
            if not other_id or other_id == user_id or other_id in seen_ids:
                continue
            seen_ids.add(other_id)

            if viewer_result is None or not viewer_result.success or viewer_result.data is None:
                output.append({
                    "success": False,
                    "user_a": user_id,
                    "user_b": other_id,
                    "error": "Your profile is unavailable",
                })
                continue

            try:
                viewing_user = viewer_result.data
                result = match.generate_reccos(viewing_user, self._generator)
                a = self._profile_dict(viewing_user)
                b = self._profile_dict(match)
                result.update(
                    user_a=str(a["student_id"]),
                    user_b=str(b["student_id"]),
                    user_a_info={field: a.get(field) for field in self.CONTACT_FIELDS},
                    user_b_info={field: b.get(field) for field in self.CONTACT_FIELDS},
                )
            except Exception as error:
                logger.exception(
                    "Unable to prepare connection %s",
                    other_id,
                )
                match.ai_suggestions = []
                result = {
                    "success": False,
                    "user_a": user_id,
                    "user_b": other_id,
                    "error": "Match suggestions unavailable",
                }
            output.append(result)
        return output
