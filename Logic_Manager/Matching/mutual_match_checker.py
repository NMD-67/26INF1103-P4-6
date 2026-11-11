"""Check mutual acceptance through the existing src.matches functions."""

from src import matches


class MutualMatchChecker:
    def get_accepted_students(self, student_id):
        result = matches.get_accepted_match(str(student_id))
        if not isinstance(result, dict) or not result.get("success"):
            return {
                "success": False,
                "accepted_student_id": [],
                "error": result.get("error", "Unable to read accepted matches")
                if isinstance(result, dict)
                else "Unable to read accepted matches",
            }
        return {
            "success": True,
            "accepted_student_id": result.get("accepted_student_id", []),
        }

    def is_mutual_match(self, student_id, target_id):
        student_id, target_id = str(student_id), str(target_id)
        if student_id == target_id:
            return False

        first = self.get_accepted_students(student_id)
        second = self.get_accepted_students(target_id)
        if not first["success"] or not second["success"]:
            return False

        return (
            target_id in {str(value) for value in first["accepted_student_id"]}
            and student_id in {str(value) for value in second["accepted_student_id"]}
        )

    def can_release_contact(self, student_id, target_id):
        return self.is_mutual_match(student_id, target_id)
