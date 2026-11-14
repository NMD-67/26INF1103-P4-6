"""Shared recommendation workflow for the CLI and Telegram."""
from Logic_Manager.Matching.scoring_pipeline import ScoringPipeline
from results.success import Success
from results.error import Error


class RecommendationService:
    def __init__(self, users, matches, scoring):
        self._users = users
        self._matches = matches
        self._scoring = scoring
        self._pipeline = ScoringPipeline(scoring, matches)

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
        scores = self._pipeline.score_candidates(profile.data, eligible.data)
        if not scores:
            return Error("AI could not score any eligible profiles. Please try again later.")
        saved = self._pipeline.save_results(student_id, scores)
        if saved["failed"] or saved["not_saved"]:
            return Error("Some recommendations could not be saved. Please try again later.")
        stored = self._matches.get_candidates_for_user(student_id)
        if not stored.success:
            return stored
        eligible_ids = {str(user.student_id) for user in eligible.data}
        return Success([user for user in stored.data if str(user.student_id) in eligible_ids])
