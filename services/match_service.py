from repositories.matches_repo import MatchesRepo
from results.error import Error
from results.result import Result
from results.success import Success
from AI_Manager.Profile_Matching.groq_scorer import GroqScorer, GroqKeyPool
from AI_Manager.Profile_Matching.repository_user_source import RepositoryUserSource
from repositories.user_repo import UserRepo
import logging

from AI_Manager.Profile_Matching.matching_service import MatchingService

logger = logging.getLogger(__name__)


class MatchService:
    def __init__(self, match_repo: MatchesRepo, user_source=None):
        self.match_repo = match_repo
        self._users = user_source
        if self._users is None:
            self._users = RepositoryUserSource(UserRepo(match_repo.pool))

    def create_match(
        self,
        student_id: str,
        candidate_id: str,
        compatibility_score: int,
        interest_score: int,
        personality_score: int,
        preferences_score: int,
        reason: str = None,
    ) -> Result:
        """Create a new match in the database."""
        success = self.match_repo.create_match(
            student_id, candidate_id, compatibility_score, reason, interest_score, personality_score, preferences_score
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

    def get_next_candidate(self, student_id: str, generated: bool = False) -> Result:
        """Revalidate stored profiles before display; filter before fresh scoring."""
        keys = None
        try:
            excluded = set(self.match_repo.get_decided_candidate_ids(student_id))
            eligible = self._users.get_candidates(student_id, exclude=excluded)
            eligible_ids = {str(user.student_id) for user in eligible}
            # Fetch all pending rows: the first may no longer satisfy preferences.
            for candidate in self.match_repo.get_candidates_for_user(student_id):
                if str(candidate.student_id) in eligible_ids:
                    return Success(data=candidate)
            if not eligible or generated:
                return Error("No new profiles match your current preferences.")
            keys = GroqKeyPool.from_env()
            service = MatchingService(GroqScorer(keys), self._users, self)
            results = service.recommend(student_id, limit=5)
            if results:
                counts = service.save(student_id, results)
                if counts["saved"]:
                    return self.get_next_candidate(student_id, True)
                return Error("Could not save recommendations. Please try again later.")
            return Error("No new recommendations are available.")
        except Exception:
            logger.exception("Could not retrieve the next recommendation")
            return Error("Recommendations are temporarily unavailable.")
        finally:
            if keys is not None:
                keys.close()

    def get_all_matches(self, student_id: str) -> Result:
        """Return profiles where both students accepted each other."""
        matches = self.match_repo.get_matches_for_user(student_id)
        if matches is None:
            return Error("Could not retrieve mutual connections")
        return Success(data=matches)

    def get_decided_candidate_ids(self, student_id: str) -> Result:
        """Return IDs of candidates this student already accepted or rejected."""
        ids = self.match_repo.get_decided_candidate_ids(student_id)
        return Success(data=ids)

    def get_mutual_connections(self, student_id: str) -> Result:
        """Return mutual connection IDs for the suggestion service."""
        result = self.get_all_matches(student_id)
        if not result.success:
            return result
        return Success(data=[str(match.student_id) for match in result.data])
