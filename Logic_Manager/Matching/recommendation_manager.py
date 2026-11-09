"""Use SITogether's existing database functions to retrieve recommendations."""

from Data_Manager.database import db
from src import matches


class RecommendationManager:
    def __init__(self):
        self._recommendations = {}
        self._current_match_index = 0

    def load_matches(self, student_id):
        """Return saved recommendations excluding previously decided profiles."""
        result = db.get_user_recco_student_id(str(student_id))
        if not isinstance(result, dict) or not result.get("success"):
            return None

        recommendations = result.get("recco_student_id") or {}
        if not isinstance(recommendations, dict):
            return None

        accepted = matches.get_accepted_match(str(student_id))
        rejected = matches.get_rejected_match(str(student_id))

        accepted_ids = set()
        rejected_ids = set()
        if isinstance(accepted, dict) and accepted.get("success"):
            accepted_ids = {str(value) for value in accepted.get("accepted_student_id", [])}
        if isinstance(rejected, dict) and rejected.get("success"):
            rejected_ids = {str(value) for value in rejected.get("rejected_student_id", [])}

        excluded = accepted_ids | rejected_ids | {str(student_id)}
        self._recommendations = {
            str(candidate_id): score
            for candidate_id, score in recommendations.items()
            if str(candidate_id) not in excluded
        }
        self._current_match_index = 0
        return self._recommendations

    @staticmethod
    def sort_matches_by_score(match_dict):
        return sorted(match_dict.items(), key=lambda item: float(item[1]), reverse=True)

    @staticmethod
    def compatibility_label(score):
        try:
            score = int(score)
        except (TypeError, ValueError):
            return None
        if not 0 <= score <= 100:
            return None
        if score >= 85:
            return "High Compatibility"
        if score >= 70:
            return "Moderate Compatibility"
        return "Low Compatibility"

    @staticmethod
    def get_next_match(match_list, current_index):
        if 0 <= current_index < len(match_list):
            return match_list[current_index]
        return None

    def get_next_user(self, student_id):
        """Get highest-scoring saved candidate, using the original result keys."""
        recommendations = self.load_matches(student_id)
        if recommendations is None:
            return {"success": False, "error": "Could not load recommendations"}

        sorted_matches = self.sort_matches_by_score(recommendations)
        if not sorted_matches:
            return {"success": False, "error": "Out of recommended students."}

        candidate_id, compatibility = sorted_matches[0]
        return {
            "success": True,
            "student_id": candidate_id,
            "compatability": compatibility,  # Keep original key expected by main.py.
        }
