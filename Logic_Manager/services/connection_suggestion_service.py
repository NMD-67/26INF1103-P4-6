"""Connect mutual matches to SuggestionsGenerator and ConsoleIO."""

import logging
from dataclasses import asdict, is_dataclass

from AI_Manager.Suggestions_generator.suggestions_generator import SuggestionsGenerator

logger = logging.getLogger(__name__)


class ConnectionSuggestionService:
    """Find mutual matches, generate their suggestions, and return UI results."""

    CONTACT_FIELDS = ("student_id", "name", "tele_handle", "insta_handle")
    SCORE_FIELDS = ("compatibility_score", "interest_score", "personality_score",
                    "preferences_score", "reason")

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
            # These profiles came from the confirmed mutual-connections query.
            # Keep their contact details even if suggestion generation fails.
            other = self._profile_dict(match)
            connection_info = {
                "user_a": user_id,
                "user_b": other_id,
                "compatibility": {field: other.get(field) for field in self.SCORE_FIELDS},
                "user_b_info": {field: other.get(field) for field in self.CONTACT_FIELDS},
            }

            if viewer_result is None or not viewer_result.success or viewer_result.data is None:
                output.append({
                    "success": False,
                    **connection_info,
                    "error": "Your profile is unavailable",
                })
                continue

            try:
                viewing_user = viewer_result.data
                result = match.generate_reccos(viewing_user, self._generator)
                a = self._profile_dict(viewing_user)
                b = self._profile_dict(match)
                result.update(
                    compatibility=connection_info["compatibility"],
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
                    **connection_info,
                    "error": "Match suggestions unavailable",
                }
            output.append(result)
        return output

    def regenerate_for_connection(
        self, user_id: str, other_id: str, feedback: str,
        previous_connection: dict,
    ) -> dict:
        """Regenerate for a verified mutual match using the student's feedback.

        Keep the last good suggestions if generation fails. Do not modify
        database records or contact permissions.
        """
        user_id, other_id = str(user_id).strip(), str(other_id).strip()
        if not feedback or not isinstance(feedback, str) or not feedback.strip() or len(feedback.strip()) > 500:
            return {"success": False, "error": "Feedback must contain 1-500 characters."}
        if not user_id or not other_id or user_id == other_id:
            return {"success": False, "error": "Invalid connection."}
        if not isinstance(previous_connection, dict) or str(previous_connection.get("user_b")) != other_id or str(previous_connection.get("user_a")) != user_id or not previous_connection.get("success"):
            return {"success": False, "error": "No valid previous suggestions for this connection."}
        try:
            # Recheck mutual match status; never regenerate against an arbitrary ID.
            matches_result = self._match_service.get_all_matches(user_id)
            if not matches_result.success or not isinstance(matches_result.data, (list, tuple)):
                raise RuntimeError("Cannot verify mutual match")
            matched = next(
                (m for m in matches_result.data if str(m.student_id).strip() == other_id),
                None,
            )
            if matched is None:
                return {"success": False, "error": "This mutual match is no longer available."}
            viewer_result = self._user_service.get_user(user_id)
            if not viewer_result.success or viewer_result.data is None:
                raise RuntimeError("Cannot load your profile")
            previous = {
                key: previous_connection.get(key, [])
                for key in SuggestionsGenerator.OUTPUT_KEYS
            }
            result = self._generator.generate_suggestions(
                self._profile_dict(viewer_result.data),
                self._profile_dict(matched),
                review_feedback=feedback.strip(),
                previous_suggestions=previous,
            )
            if not result.get("success"):
                return {"success": False, "error": result.get("error", "Regeneration failed")}
            # Preserve display information and only replace suggestion lists.
            return {
                **previous_connection,
                **{key: result[key] for key in SuggestionsGenerator.OUTPUT_KEYS},
                "success": True,
            }
        except Exception:
            logger.exception("Unable to regenerate suggestions for connection %s", other_id)
            return {"success": False, "error": "Unable to regenerate suggestions right now."}
