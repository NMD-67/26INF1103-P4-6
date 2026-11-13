"""Validate individual profile answers without terminal or database access."""
from Logic_Manager.profile_logic_manager import ProfileLogicManager


class ProfileValidator:
    MIN_AGE = 18
    MAX_AGE = 30
    MAX_LIST_ITEMS = 10
    MAX_ITEM_LEN = 40
    LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    DIGITS = "0123456789"

    def __init__(self, profile_logic=None):
        self._logic = profile_logic if profile_logic is not None else ProfileLogicManager()

    def _validate_student_id(self, raw, field):
        if raw.isascii() and raw.isdecimal() and len(raw) == 7:
            return raw, None

        return None, "Student ID must be exactly 7 digits."

    def _validate_name(self, raw, field):
        error = "Name must be 2-60 letters (spaces, . ' - allowed)."
        if len(raw) < 2 or len(raw) > 60:
            return None, error
        if raw[0] not in self.LETTERS:
            return None, error
        for character in raw:
            if character not in self.LETTERS + " .'-":
                return None, error
        return " ".join(raw.split()), None

    def _validate_date(self, raw, field):
        try:
            born = self._logic.parse_birthday(raw)
        except ValueError:
            return None, "Use a real date in DD/MM/YYYY format."
        age = self._logic.calculate_age(born)
        if not self.MIN_AGE <= age <= self.MAX_AGE:
            return None, f"Age must be between {self.MIN_AGE} and {self.MAX_AGE}."
        return raw, None

    def _validate_choice(self, raw, field):
        options = field["options"]
        if raw.isdecimal() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1], None
        for option in options:
            if raw.lower() == option.lower():
                return option, None
        return None, f"Pick a number 1-{len(options)} or type one of the options."

    def _validate_multi_choice(self, raw, field):
        selected = []
        for part in raw.split(","):
            value, error = self._validate_choice(part.strip(), field)
            if error:
                return None, error
            if value not in selected:
                selected.append(value)
        if "No preference" in selected:
            if len(selected) > 1:
                return None, "Choose No preference on its own, or select items to exclude."
            return [], None
        return selected, None

    def _validate_mbti(self, raw, field):
        if raw.upper() in field["options"]:
            return raw.upper(), None
        return None, "Enter one of the 16 MBTI types, e.g. INTJ."

    def _validate_text(self, raw, field):
        if field["min_len"] <= len(raw) <= field["max_len"]:
            return raw, None
        return None, f"Must be {field['min_len']}-{field['max_len']} characters."

    def _validate_telegram(self, raw, field):
        handle = raw.lstrip("@")
        error = "Telegram handle: 5-32 chars, letters/digits/underscore, starts with a letter."
        if len(handle) < 5 or len(handle) > 32:
            return None, error
        if handle[0] not in self.LETTERS:
            return None, error
        for character in handle:
            if character not in self.LETTERS + self.DIGITS + "_":
                return None, error
        return "@" + handle, None

    def _validate_instagram(self, raw, field):
        handle = raw
        if handle.startswith("@"):
            handle = handle[1:]
        error = "Enter an Instagram username using 1-30 letters, digits, periods or underscores; not a link."
        if len(handle) < 1 or len(handle) > 30:
            return None, error
        for character in handle:
            if character not in self.LETTERS + self.DIGITS + "_.":
                return None, error
        return "@" + handle.lower(), None

    def _validate_list(self, raw, field):
        items = []
        for part in raw.split(","):
            item = part.strip()
            if not item:
                continue
            duplicate = False
            for saved_item in items:
                if item.lower() == saved_item.lower():
                    duplicate = True
                    break
            if not duplicate:
                items.append(item)
        if not items:
            return None, "Enter at least one item."
        error = f"Max {self.MAX_LIST_ITEMS} items, each up to {self.MAX_ITEM_LEN} characters."
        if len(items) > self.MAX_LIST_ITEMS:
            return None, error
        for item in items:
            if len(item) > self.MAX_ITEM_LEN:
                return None, error
        return items, None

    def _validate_age(self, raw, field):
        try:
            age = int(raw)
        except ValueError:
            return None, "Enter a whole number."

        if not self.MIN_AGE <= age <= self.MAX_AGE:
            return None, f"Enter an age between {self.MIN_AGE} and {self.MAX_AGE}."

        return age, None

    def validate_field(self, raw, field):
        """Validate one CLI or Telegram answer without prompting or printing."""
        raw = raw.strip()
        if not raw:
            if field["required"]:
                return None, "This field is required."
            if field["kind"] in ("list", "multi_choice"):
                return [], None
            return None, None

        kind = field["kind"]
        if kind == "student_id":
            return self._validate_student_id(raw, field)
        elif kind == "name":
            return self._validate_name(raw, field)
        elif kind == "date":
            return self._validate_date(raw, field)
        elif kind == "choice":
            return self._validate_choice(raw, field)
        elif kind == "multi_choice":
            return self._validate_multi_choice(raw, field)
        elif kind == "mbti":
            return self._validate_mbti(raw, field)
        elif kind == "text":
            return self._validate_text(raw, field)
        elif kind == "telegram":
            return self._validate_telegram(raw, field)
        elif kind == "instagram":
            return self._validate_instagram(raw, field)
        elif kind == "list":
            return self._validate_list(raw, field)
        elif kind == "age":
            return self._validate_age(raw, field)
        raise KeyError(kind)
