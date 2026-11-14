"""Shared CLI/Telegram profile mapping, validation and completeness rules."""
from datetime import date
from config.user_fields import USER_FIELD_CONFIG, PROFILE_FIELDS
from Logic_Manager.profile_logic_manager import ProfileLogicManager
from IO_Manager.profile_validator import ProfileValidator
from models.dealbreaker import DealBreaker


class ProfileForm:
    def __init__(self, logic=None, config=None, fields=None, dealbreaker_class=DealBreaker):
        self._fields = PROFILE_FIELDS if fields is None else fields
        self._config = USER_FIELD_CONFIG if config is None else config
        self._logic = logic if logic is not None else ProfileLogicManager(self._fields)
        self._validator = ProfileValidator(self._logic)
        self._dealbreaker_class = dealbreaker_class

    def form_values(self, profile):
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
            # Preserve all selected blacklist values when loading the form.
            values["race_preference"] = preferences.race
            values["religion_preference"] = preferences.religion
        return values

    def _preference_list(self, value):
        if value is None or value == "" or value in ("No preference", "Prefer not to say"):
            return []
        return value.copy() if isinstance(value, list) else [value]

    def storage_values(self, answers):
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
        ).to_row()
        return updates

    def questions_for_profile(self, answers):
        # Existing users with both derived fields need not re-enter their birthday.
        if answers.get("age") is not None and answers.get("horoscope"):
            return [field for field in self._fields if field["key"] != "birthday"]
        return self._fields

    def missing_fields(self, answers):
        return self._logic.find_missing_fields(answers, self.questions_for_profile(answers))

    def apply_answer(self, answers, field, raw):
        if self._logic.should_skip_field(answers, field):
            return "This field does not apply to your profile."
        value, error = self._validator.validate_field(raw, field)
        if error:
            return error
        proposed = {**answers, field["key"]: value}
        if field["key"] in ("min_preferred_age", "max_preferred_age"):
            error = self._logic.validate_age_preferences(proposed)
            if error:
                return error
        answers[field["key"]] = value
        for other in self._fields:
            if self._logic.should_skip_field(answers, other):
                self._logic.clear_field(answers, other)
        return None

    def should_skip(self, answers, field):
        return self._logic.should_skip_field(answers, field)

    def validate_for_save(self, answers):
        if self.missing_fields(answers):
            return "Some required fields are still missing."
        return self._logic.validate_age_preferences(answers)
