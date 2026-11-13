"""Profile completeness rules converted from the Part 1 logic_manager.py.

This class does not perform input/output or database operations.
"""

from datetime import date, datetime


class ProfileLogicManager:
    def __init__(self, profile_fields: list[dict] | None = None):
        self._profile_fields = profile_fields if profile_fields is not None else []

    def should_skip_field(self, profile: dict, field: dict) -> bool:
        """Check whether a field's skip_if condition is met."""
        condition = field.get("skip_if")
        if not condition:
            return False
        return profile.get(condition["field"]) in condition["in"]

    def find_missing_fields(
        self, profile: dict, fields: list[dict] | None = None
    ) -> list[dict]:
        """Return required profile fields with no meaningful value."""
        fields = self._profile_fields if fields is None else fields
        missing = []

        for field in fields:
            if not field.get("required", False):
                continue
            if self.should_skip_field(profile, field):
                continue

            value = profile.get(field["key"])
            if isinstance(value, str):
                value = value.strip()
            elif isinstance(value, list):
                value = [
                    str(item).strip()
                    for item in value
                    if item is not None and str(item).strip()
                ]

            if not value:
                missing.append(field)

        return missing

    def is_profile_complete(
        self, profile: dict, fields: list[dict] | None = None
    ) -> bool:
        """True when no required fields are missing."""
        return not self.find_missing_fields(profile, fields)

    def clear_field(self, profile: dict, field: dict) -> None:
        """Reset one field in the same way as the Part 1 code."""
        profile[field["key"]] = [] if field["kind"] == "list" else None

    def validate_age_preferences(self, profile):
        minimum = profile.get("min_preferred_age")
        maximum = profile.get("max_preferred_age")

        for age in (minimum, maximum):
            if age is None:
                continue

            if type(age) is not int:
                return "Preferred ages must be whole numbers."

            if not 18 <= age <= 30:
                return "Preferred ages must be between 18 and 30."

        if minimum is not None and maximum is not None:
            if minimum > maximum:
                return "Minimum preferred age cannot exceed maximum preferred age."

        return None

    def parse_birthday(self, text):
        return datetime.strptime(text, "%d/%m/%Y").date()

    def calculate_age(self, birthday, today=None):
        today = date.today() if today is None else today
        age = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1
        return age

    def calculate_horoscope(self, birthday: date) -> str:
        """Return the conventional Western sun sign without calling any AI API."""
        month_day = (birthday.month, birthday.day)
        signs = (
            ((1, 20), (2, 18), "Aquarius"),
            ((2, 19), (3, 20), "Pisces"),
            ((3, 21), (4, 19), "Aries"),
            ((4, 20), (5, 20), "Taurus"),
            ((5, 21), (6, 20), "Gemini"),
            ((6, 21), (7, 22), "Cancer"),
            ((7, 23), (8, 22), "Leo"),
            ((8, 23), (9, 22), "Virgo"),
            ((9, 23), (10, 22), "Libra"),
            ((10, 23), (11, 21), "Scorpio"),
            ((11, 22), (12, 21), "Sagittarius"),
        )
        for start, end, sign in signs:
            if start <= month_day <= end:
                return sign
        return "Capricorn"  # 22 Dec through 19 Jan

    def process_birthday(self, text: str, today: date | None = None) -> dict:
        """Calculate values locally; deliberately do not return full birthday."""
        birthday = self.parse_birthday(text)
        return {
            "age": self.calculate_age(birthday, today=today),
            "horoscope": self.calculate_horoscope(birthday),
        }
