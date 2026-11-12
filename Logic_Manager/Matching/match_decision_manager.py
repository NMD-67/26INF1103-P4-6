"""Original accept/reject logic in a class; no new database connection."""

from src import matches
from .mutual_match_checker import MutualMatchChecker


class MatchDecisionManager:
    VALID_DECISIONS = ("accept", "reject")

    def __init__(self):
        self._mutual_checker = MutualMatchChecker()

    @classmethod
    def check_user_decision(cls, decision):
        return str(decision).strip().lower() in cls.VALID_DECISIONS

    def create_match_decision(self, student_id, target_id, decision):
        student_id = str(student_id).strip()
        target_id = str(target_id).strip()
        decision = str(decision).strip().lower()
        if not student_id or not target_id or student_id == target_id:
            return None
        if not self.check_user_decision(decision):
            return None
        return {
            "student_id": student_id,
            "target_id": target_id,
            "decision": decision,
        }

    def record_accept(self, student_id, target_id):
        choice = self.create_match_decision(student_id, target_id, "accept")
        if choice is None:
            return {"success": False, "error": "Invalid accept decision"}

        current = self._mutual_checker.get_accepted_students(choice["student_id"])
        if not current["success"]:
            return current

        if choice["target_id"] not in {str(v) for v in current["accepted_student_id"]}:
            result = matches.add_accepted_match(choice["student_id"], [choice["target_id"]])
            if not isinstance(result, dict) or not result.get("success"):
                return {"success": False, "error": result.get("error", "Unable to save accept") if isinstance(result, dict) else "Unable to save accept"}

        removed = matches.remove_recco_student_id(choice["student_id"], [choice["target_id"]])
        return {
            "success": True,
            "decision": "accept",
            "student_id": choice["student_id"],
            "target_id": choice["target_id"],
            "recommendation_removed": isinstance(removed, dict) and bool(removed.get("success")),
        }

    def record_reject(self, student_id, target_id):
        choice = self.create_match_decision(student_id, target_id, "reject")
        if choice is None:
            return {"success": False, "error": "Invalid reject decision"}

        current = self._mutual_checker.get_accepted_students(choice["student_id"])
        if not current["success"]:
            return current

        if choice["target_id"] in {str(v) for v in current["accepted_student_id"]}:
            removed = matches.remove_accepted_match(choice["student_id"], [choice["target_id"]])
            if not isinstance(removed, dict) or not removed.get("success"):
                return {"success": False, "error": "Unable to remove previous accepted match"}

        result = matches.add_rejected_match(choice["student_id"], [choice["target_id"]])
        if not isinstance(result, dict) or not result.get("success"):
            return {"success": False, "error": result.get("error", "Unable to save reject") if isinstance(result, dict) else "Unable to save reject"}

        removed = matches.remove_recco_student_id(choice["student_id"], [choice["target_id"]])
        return {
            "success": True,
            "decision": "reject",
            "student_id": choice["student_id"],
            "target_id": choice["target_id"],
            "recommendation_removed": isinstance(removed, dict) and bool(removed.get("success")),
        }

    def handle_match_decision(self, student_id, target_id, decision):
        choice = self.create_match_decision(student_id, target_id, decision)
        if choice is None:
            return self._outcome(False, "error", "Decision must be accept or reject")

        if choice["decision"] == "reject":
            result = self.record_reject(student_id, target_id)
            if not result["success"]:
                return self._outcome(False, "error", result.get("error"))
            return self._outcome(True, "rejected")

        result = self.record_accept(student_id, target_id)
        if not result["success"]:
            return self._outcome(False, "error", result.get("error"))

        if self._mutual_checker.is_mutual_match(student_id, target_id):
            return self._outcome(True, "matched")
        return self._outcome(True, "waiting")

    @staticmethod
    def _outcome(success, status, error=None):
        mutual = status == "matched"
        response = {
            "success": success,
            "status": status,
            "matched": mutual,
            "release_contact": mutual,
        }
        if error:
            response["error"] = error
        return response
