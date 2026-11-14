"""Shared recommendation workflow for the CLI and Telegram."""
from Logic_Manager.Matching.score_calculator import ScoreCalculator
from results.success import Success
from results.error import Error


class RecommendationService:
    def __init__(self, users, matches, scoring):
        self._users = users
        self._matches = matches
        self._scoring = scoring
        self._calculator = ScoreCalculator()

    def eligible_users(self, student_id):
        eligible = self._users.filter_users_by_dealbreaker(student_id)
        if eligible is None:
            return Error("Candidate filtering is unavailable.")
        if not eligible.success:
            return eligible
        decisions = self._matches.get_decided_candidate_ids(student_id)
        if not decisions.success:
            return decisions
        excluded = {str(value) for value in decisions.data}
        excluded.add(str(student_id))
        return Success([user for user in eligible.data if str(user.student_id) not in excluded])

    def get_recommendations(self, student_id):
        if not self._scoring.prepare():
            return Error("AI matching is unavailable. Check the scoring API credentials. You can still use the other menu options.")
        eligible = self.eligible_users(student_id)
        if not eligible.success or not eligible.data:
            return eligible
        profile = self._users.get_profile(student_id)
        if not profile.success:
            return profile
        for candidate in eligible.data:
            score = self._scoring.score(profile.data, candidate)
            if score is None:
                continue
            result = self._matches.create_match(
                student_id=student_id,
                candidate_id=candidate.student_id,
                compatibility_score=self._calculator.overall(score.categories),
                interest_score=score.categories.interests_lifestyle,
                personality_score=score.categories.personality_values,
                preferences_score=score.categories.relationship_goals,
                reason=score.reason,
            )
            if not result.success:
                return result
        stored = self._matches.get_candidates_for_user(student_id)
        if not stored.success:
            return stored
        eligible_ids = {str(user.student_id) for user in eligible.data}
        return Success([user for user in stored.data if str(user.student_id) in eligible_ids])
