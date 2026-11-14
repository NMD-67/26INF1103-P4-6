"""Coordinate the SITogether CLI using the application services."""

import asyncio
import logging
from IO_Manager.profile_form import ProfileForm
from Logic_Manager.services.recommendation_service import RecommendationService

logger = logging.getLogger(__name__)


class SITogetherApp:
    def __init__(self, user_service, otp_service, match_service,
                 scoring_manager, suggestion_manager, profile_io,
                 profile_logic, field_config, profile_fields, dealbreaker_class):
        self._users = user_service
        self._otp = otp_service
        self._matches = match_service
        self._scoring = scoring_manager
        self._suggestions = suggestion_manager
        self._io = profile_io
        self._logic = profile_logic
        self._config = field_config
        self._fields = profile_fields
        self._dealbreaker_class = dealbreaker_class
        self._student_id = None
        self._profile_form = ProfileForm(profile_logic, field_config, profile_fields, dealbreaker_class)

    def login(self):
        student_id = self._io.ask_student_id()
        result = asyncio.run(self._otp.send_otp(student_id))
        if not result.success:
            self._io.show_error(result.error_msg)
            return False
        self._io.show("Check your school email for the OTP.")
        for attempt in range(3):
            otp = self._io.ask_otp()
            result = self._otp.verify_otp(student_id, otp, self._users)
            if result.success:
                self._student_id = student_id
                return True
            self._io.show_error(result.error_msg)
        self._io.show("Login unsuccessful. Please restart to try again.")
        return False

    def _load_profile(self):
        result = self._users.get_profile(self._student_id)
        if not result.success:
            raise ValueError(result.error_msg)
        return result.data

    def _form_values(self, profile):
        return self._profile_form.form_values(profile)

    def _storage_values(self, answers):
        return self._profile_form.storage_values(answers)

    def _save_profile(self, answers):
        result = self._users.update_user(
            self._student_id, self._storage_values(answers)
        )
        if not result.success:
            self._io.show_error(result.error_msg)
            return False
        return True

    def _questions_for_profile(self, answers):
        return self._profile_form.questions_for_profile(answers)

    def complete_profile(self):
        answers = self._form_values(self._load_profile())
        questions = self._questions_for_profile(answers)
        missing = self._logic.find_missing_fields(answers, questions)
        if not missing:
            return True
        self._io.show("Please complete your profile.")
        preset = {key: value for key, value in answers.items()
                  if value not in (None, "", [])}
        preset["student_id"] = self._student_id
        answers = self._io.collect_profile(questions, preset)
        self._io.show_profile(answers)
        if not self._io.confirm("Save this profile?"):
            return False
        if self._save_profile_with_retry(answers):
            return True
        self._io.show("Leaving SITogether without completing profile setup.")
        return False

    def _save_profile_with_retry(self, answers):
        """Keep the same answers until saving succeeds or the user cancels."""
        while True:
            try:
                if self._save_profile(answers):
                    return True
            except Exception:
                logger.exception("Profile save failed")
                self._io.show_error("Could not save your profile. Your answers are still available for retry.")
            if not self._io.confirm("Try saving this profile again?"):
                self._io.show("Unsaved changes discarded.")
                return False

    def view_profile(self):
        answers = self._form_values(self._load_profile())
        self._io.show_profile(answers)

    def update_profile(self):
        answers = self._form_values(self._load_profile())
        fields = [field for field in self._fields if field["key"] != "student_id"]
        changed = False
        while True:
            field = self._io.ask_edit_field(fields)
            if field is None:
                break
            if self._logic.should_skip_field(answers, field):
                self._io.show("This field does not apply to your profile.")
                continue
            answers[field["key"]] = self._io.ask_profile_field(field, answers)
            changed = True
            for other in fields:
                if self._logic.should_skip_field(answers, other):
                    self._logic.clear_field(answers, other)
            missing = self._logic.find_missing_fields(
                answers, self._questions_for_profile(answers)
            )
            if missing:
                answers.update(self._io.collect_missing(missing))
        if changed and self._io.confirm("Save these changes?"):
            self._save_profile_with_retry(answers)

    def view_matches(self):
        self._io.show("Finding compatible profiles. Please wait...")
        recommendations = RecommendationService(self._users, self._matches, self._scoring)
        result = recommendations.get_recommendations(self._student_id)
        if not result.success:
            self._io.show_error(result.error_msg)
            return
        if not result.data:
            self._io.show("No new profiles match your current preferences.")
            return
        for candidate in result.data:
            self._io.show_candidate(candidate)
            decision = self._io.ask_match_decision()
            if decision == "0":
                return
            saved = self._matches.handle_candidate_decision(
                self._student_id, candidate.student_id, decision == "accept"
            )
            self._io.show("Decision saved." if saved.success else saved.error_msg)

    def view_connections(self):
        connections = self._suggestions.get_matches_for_user(self._student_id)
        if not connections:
            self._io.show_connections(connections)
            return
        for connection in connections:
            self._io.show_connections([connection])
            if not connection.get("success"):
                continue
            # Each user-requested regeneration is a separate Groq request.
            # The previous successful suggestions remain visible on failure.
            for regeneration in range(3):
                if self._io.ask_suggestion_decision() == "1":
                    break
                feedback = self._io.ask_suggestion_feedback()
                if feedback is None:
                    break
                new_result = self._suggestions.regenerate_for_connection(
                    self._student_id,
                    connection["user_b"],
                    feedback,
                    connection,
                )
                if not new_result.get("success"):
                    self._io.show_error(
                        "Could not regenerate suggestions. Keeping the previous suggestions."
                    )
                    continue
                connection = new_result
                self._io.show_connections([connection])
            else:
                self._io.show("Regeneration limit reached. Keeping the latest suggestions.")

    def run(self):
        self._io.show("Welcome to SITogether")
        if not self.login() or not self.complete_profile():
            return
        while True:
            choice = self._io.ask_menu_choice()
            try:
                if choice == "1":
                    self.view_matches()
                elif choice == "2":
                    self.view_connections()
                elif choice == "3":
                    self.view_profile()
                elif choice == "4":
                    self.update_profile()
                elif choice == "5":
                    if self._io.confirm("Permanently delete your account?"):
                        result = self._users.delete_user(self._student_id)
                        if result.success:
                            self._io.show("Account deleted.")
                            return
                        self._io.show_error(result.error_msg)
                elif choice == "6":
                    self._io.show("Goodbye! Thanks for using SITogether.")
                    return
            except Exception:
                logger.exception("Menu operation failed")
                self._io.show_error("Could not complete this option. Please try again.")

