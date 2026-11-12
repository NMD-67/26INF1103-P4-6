"""Coordinate the SITogether CLI using the application services."""

import asyncio
import logging
from datetime import date

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
        """Translate a loaded model into the existing form's field names."""
        details = profile.get_user_details()
        values = {}
        for key, settings in self._config.items():
            form_key = settings.get("form_key", key)
            value = details.get(key, details.get(form_key))

            if form_key == "birthday" and isinstance(value, date):
                value = value.strftime("%d/%m/%Y")

            values[form_key] = value
        preferences = profile.dealbreakers
        if preferences is not None:
            values["min_preferred_age"] = preferences.min_age
            values["max_preferred_age"] = preferences.max_age
            # The current form is single-choice; do not silently discard a
            # previously stored multi-selection when editing unrelated fields.
            values["race_preference"] = preferences.race
            values["religion_preference"] = preferences.religion
        return values

    def _preference_list(self, value):
        if value is None or value == "" or value in ("No preference", "Prefer not to say"):
            return []
        return value.copy() if isinstance(value, list) else [value]

    def _storage_values(self, answers):
        """Map form answers to the repository contract; perform no SQL here."""
        preference_keys = {"race_preference", "religion_preference",
                           "min_preferred_age", "max_preferred_age"}
        updates = {}
        for key, settings in self._config.items():
            form_key = settings.get("form_key", key)
            if key == "student_id" or form_key == "birthday" or form_key in preference_keys:
                continue
            if form_key not in answers:
                continue
            value = answers[form_key]
            if settings["storage"] is None:
                if value not in (None, "", []):
                    raise ValueError(f"Storage for {form_key} is not configured yet.")
                continue
            if settings.get("editable", False):
                updates[key] = value

        # Birthday is used only in memory; never pass it to the repository.
        if answers.get("birthday"):
            updates.update(self._logic.process_birthday(answers["birthday"]))

        gender = answers.get("match_preference")
        updates["dealbreakers"] = self._dealbreaker_class(
            min_age=answers.get("min_preferred_age") or None,
            max_age=answers.get("max_preferred_age") or None,
            race=self._preference_list(answers.get("race_preference")),
            religion=self._preference_list(answers.get("religion_preference")),
            gender=None if gender == "Both" else gender,
        )
        return updates

    def _save_profile(self, answers):
        result = self._users.update_user(
            self._student_id, self._storage_values(answers)
        )
        if not result.success:
            self._io.show_error(result.error_msg)
            return False
        return True

    def _questions_for_profile(self, answers):
        # Existing users with both derived fields need not re-enter their birthday.
        if answers.get("age") is not None and answers.get("horoscope"):
            return [field for field in self._fields if field["key"] != "birthday"]
        return self._fields

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
        return self._save_profile(answers)

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
            self._save_profile(answers)

    def view_matches(self):
        self._io.show("Finding compatible profiles. Please wait...")
        eligible = self._users.filter_users_by_dealbreaker(self._student_id)
        if eligible is None:
            self._io.show_error("Candidate filtering has not been implemented yet.")
            return
        if not eligible.success:
            self._io.show_error(eligible.error_msg)
            return
        user = self._load_profile()
        scores = self._scoring.match_candidates(user, eligible.data)
        for score in scores:
            result = self._matches.create_match(
                self._student_id, score.matched_user,
                score.compatibility_score, score.reason,
            )
            if not result.success:
                self._io.show_error(result.error_msg)
                return
        result = self._matches.get_candidates_for_user(self._student_id)
        if not result.success:
            self._io.show_error(result.error_msg)
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
        self._io.show_connections(connections)

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

