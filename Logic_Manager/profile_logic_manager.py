"""Profile completeness rules converted from the Part 1 logic_manager.py.

This class does not perform input/output or database operations.
"""


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
