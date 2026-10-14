"""Domain logic for profiles: completeness checks

No printing, no file access, no API calls.
"""
from datetime import datetime

def parse_birthday(text):
    """Convert a DD/MM/YYYY string to a date."""
    return datetime.strptime(text, "%d/%m/%Y").date()


def should_skip_field(profile, field):
    """Return True if this field's skip_if condition is met by earlier answers."""
    condition = field.get("skip_if")
    if not condition:
        return False
    return profile.get(condition["field"]) in condition["in"]


def find_missing_fields(profile, fields):
    missing = []

    for field in fields:
        if not field["required"]:
            continue

        if should_skip_field(profile, field):
            continue

        value = profile.get(field["key"])

        if isinstance(value, str):
            value = value.strip()

        elif isinstance(value, list):
            cleaned_items = []

            for item in value:
                if item is None:
                    continue

                text = str(item).strip()

                if text:
                    cleaned_items.append(text)

            value = cleaned_items

        if not value:
            missing.append(field)

    return missing


def is_profile_complete(profile, fields):
    """A profile is complete when no required field is missing."""
    missing = find_missing_fields(profile, fields)
    return len(missing) == 0

def clear_field(profile, field):
    if field["kind"] == "list":
        profile[field["key"]] = []
    else:
        profile[field["key"]] = None