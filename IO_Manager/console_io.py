"""Own console interaction; delegate validation and profile rules to objects."""
from config.user_fields import PROFILE_FIELDS, PROFILE_DISPLAY_FIELDS
from Logic_Manager.profile_logic_manager import ProfileLogicManager
from IO_Manager.profile_validator import ProfileValidator


class ConsoleIO:
    def __init__(self, profile_fields=None, profile_logic=None, validator=None,
                 read=None, write=None):
        self._fields = PROFILE_FIELDS if profile_fields is None else profile_fields
        self._logic = profile_logic if profile_logic is not None else ProfileLogicManager(self._fields)
        self._validator = validator if validator is not None else ProfileValidator(self._logic)
        self._read = read if read is not None else input
        self._write = write if write is not None else print

    def validate_field(self, raw, field):
        return self._validator.validate_field(raw, field)

    def show(self, message: str = ""):
        self._write(message)

    def show_error(self, message):
        self._write(f"  [!] {message}")

    def show_section(self, title):
        self._write(f"\n=== {title} ===")

    def _show_options(self, field):
        if field["kind"] in ("choice", "multi_choice"):
            for number, option in enumerate(field["options"], start=1):
                self._write(f"    {number}. {option}")

    def ask_field(self, field):
        """Prompt until the answer is valid; optional fields can be skipped with Enter."""
        self._show_options(field)
        suffix = ""
        if field.get("hint"):
            suffix = f" [{field['hint']}]"
        if not field["required"]:
            suffix += " (optional, Enter to skip)"
        while True:
            raw = self._read(f"{field['question']}{suffix} ").strip()
            value, error = self.validate_field(raw, field)
            if error:
                self.show_error(error)
                continue
            return value

    def ask_profile_field(self, field, profile):
        while True:
            value = self.ask_field(field)

            if field["key"] in ("min_preferred_age", "max_preferred_age"):
                proposed_profile = profile.copy()
                proposed_profile[field["key"]] = value

                error = self._logic.validate_age_preferences(proposed_profile)

                if error:
                    self.show_error(error)
                    continue

            return value

    def collect_profile(self, fields, preset):
        """Ask every field not already in `preset`, grouped by section.

        A field whose skip_if condition is met by earlier answers is set to an
        empty value (None, or [] for list fields) without being asked at all.
        """
        profile = dict(preset)
        current_section = None
        for field in fields:
            if field["key"] in profile:
                continue
            if self._logic.should_skip_field(profile, field):
                self._logic.clear_field(profile, field)
                continue
            if field["section"] != current_section:
                current_section = field["section"]
                self.show_section(current_section)
            profile[field["key"]] = self.ask_profile_field(field, profile)
        return profile

    def collect_missing(self, missing):
        """Re-prompt only for the required fields that are still empty."""
        self.show("\nSome required fields are still missing:")
        answers = {}
        for field in missing:
            answers[field["key"]] = self.ask_field(field)
        return answers

    def confirm(self, question):
        """Ask a yes/no question until the answer is valid."""
        while True:
            answer = self._read(f"{question} (y/n): ").strip().lower()
            if answer in ("y", "yes"):
                return True
            if answer in ("n", "no"):
                return False
            self.show_error("Please answer y or n.")

    def profile_label(self, key):
        for field in self._fields:
            if field["key"] == key:
                return field["label"]

        return key.replace("_", " ").title()

    def profile_value(self, key, value):
        """Use friendly display text without changing the stored profile value."""
        if key == "here_for" and isinstance(value, str) and value.strip().lower() == "both":
            return "Relationships and Friends"
        if key in ("race_preference", "religion_preference") and not value:
            return "None"
        if key in ("min_preferred_age", "max_preferred_age") and value is None:
            return "No limit"
        return self._format_value(value)

    def _format_value(self, value):
        if not value:
            return "-"
        if isinstance(value, list):
            return ", ".join(value)
        return str(value)

    def show_profile(self, profile):
        display_profile = profile.copy()
        if display_profile.get("birthday"):
            display_profile.update(self._logic.process_birthday(display_profile["birthday"]))
        self.show_profile_summary(display_profile, PROFILE_DISPLAY_FIELDS)

    def show_profile_summary(self, profile, fields):
        current_section = None

        for field in fields:
            if field["section"] != current_section:
                current_section = field["section"]
                self.show_section(current_section)

            key = field["key"]
            label = self.profile_label(key)
            value = self.profile_value(key, profile.get(key))

            self.show(f"  {label}: {value}")

    def ask_student_id(self):
        field = next(field for field in self._fields if field["key"] == "student_id")
        return self.ask_field(field)

    def ask_otp(self):
        return self._read("Enter your OTP: ").strip()

    def ask_menu_choice(self):
        self.show("\n1. Find matches\n2. View connections\n3. My profile"
                  "\n4. Update profile\n5. Delete account\n6. Quit")
        while True:
            choice = self._read("Choose an option: ").strip()
            if choice in ("1", "2", "3", "4", "5", "6"):
                return choice
            self.show_error("Choose an option from 1 to 6.")

    def ask_edit_field(self, fields):
        for number, field in enumerate(fields, 1):
            self.show(f"{number}. {field['label']}")
        while True:
            choice = self._read("Choose a field to update (0 to finish): ").strip()
            if choice == "0":
                return None
            if choice.isdecimal() and 1 <= int(choice) <= len(fields):
                return fields[int(choice) - 1]
            self.show_error("Choose a valid field number.")

    def ask_match_decision(self):
        while True:
            decision = self._read("Enter accept, reject, or 0 to return: ").strip().lower()
            if decision in ("accept", "reject", "0"):
                return decision
            self.show_error("Enter accept, reject, or 0.")

    def show_candidate(self, candidate):
        self.show(f"\nCompatibility: {candidate.compatibility_score}%")
        self.show(f"Reason: {candidate.reason or '-'}")
        for key in ("name", "year", "course", "bio", "here_for", "hobbies"):
            self.show(f"{self.profile_label(key)}: "
                      f"{self.profile_value(key, getattr(candidate, key, None))}")

    def show_connections(self, connections):
        if not connections:
            self.show("No mutual connections yet.")
        for connection in connections:
            self.show(self.format_recommendations(connection))

    def format_recommendations(self, result: dict, for_user='a'):
        other = result.get('user_b_info' if for_user == 'a' else 'user_a_info')
        if other is None:
            return "Sorry, we couldn't load your connections right now."
        lines = [f"You matched with {other.get('name') or 'someone new'}!"]
        telegram = other.get('tele_handle') or other.get('telegram_handle')
        if telegram:
            lines.append(f'Telegram: {telegram}')
        if other.get('insta_handle'):
            lines.append(f"Instagram: {other['insta_handle']}")
        if not result.get('success'):
            lines.extend(['', 'Suggestions are temporarily unavailable. Please try again later.'])
            return '\n'.join(lines)
        for title, key in (
            ('Things you have in common', 'common_interests'),
            ('Conversation starters', 'conversation_starters'),
            ('Outing ideas', 'outing_ideas'),
        ):
            lines.extend(['', f'{title}:'])
            lines.extend(f'- {item}' for item in result[key])
        return '\n'.join(lines)
