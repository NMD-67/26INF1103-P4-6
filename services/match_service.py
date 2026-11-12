from repositories.matches_repo import MatchesRepo
from results.error import Error
from results.result import Result
from results.success import Success


class MatchService:
    def __init__(self, match_repo: MatchesRepo):
        self.match_repo = match_repo

    def create_match(
        self,
        student_id: str,
        candidate_id: str,
        compatibility_score: float,
        reason: str = None,
    ) -> Result:
        """Create a new match in the database."""
        success = self.match_repo.create_match(
            student_id, candidate_id, compatibility_score, reason
        )
        if success:
            return Success(data={"message": "Match created successfully"})
        else:
            return Error(error_msg="Match already exists")

    def get_candidates_for_user(self, user_id: str) -> Result:
        """Retrieve candidates for a specific user."""
        candidates = self.match_repo.get_candidates_for_user(user_id)
        if candidates:
            return Success(data=candidates)
        else:
            return Error(error_msg=f"No candidates found for user with ID {user_id}")

    def handle_candidate_decision(
        self, student_id: str, candidate_id: str, accepted: bool
    ) -> Result:
        """Handles user action for a candidate (Accept/Reject)"""
        decision = "accepted" if accepted else "rejected"
        success = self.match_repo.edit_status(student_id, candidate_id, decision)
        if success:
            return Success("Status Updated")
        return Error("Failed to update status")

    def get_next_candidate(self, student_id: str) -> Result:
        candidates = self.match_repo.get_candidates_for_user(student_id, True)
        if len(candidates) > 0:
            return Success(data=candidates)
        else:
            # Populate candidate list
            return Error(error_msg=f"No candidates found for user with ID {student_id}")

    def get_all_matches(self, student_id: str) -> Result:
        """Return profiles where both students accepted each other."""
        matches = self.match_repo.get_matches_for_user(student_id)
        if matches is None:
            return Error("Could not retrieve mutual connections")
        return Success(data=matches)

    def get_mutual_connections(self, student_id: str) -> Result:
        """Return mutual connection IDs for the suggestion service."""
        result = self.get_all_matches(student_id)
        if not result.success:
            return result
        return Success(data=[str(match.student_id) for match in result.data])
