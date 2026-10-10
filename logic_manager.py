"""Domain logic for profiles: completeness checks and MBTI personality names.

No printing, no file access, no API calls.
"""
from datetime import datetime

PERSONALITIES = {
    "INTJ": "Architect", "INTP": "Logician", "ENTJ": "Commander", "ENTP": "Debater",
    "INFJ": "Advocate", "INFP": "Mediator", "ENFJ": "Protagonist", "ENFP": "Campaigner",
    "ISTJ": "Logistician", "ISFJ": "Defender", "ESTJ": "Executive", "ESFJ": "Consul",
    "ISTP": "Virtuoso", "ISFP": "Adventurer", "ESTP": "Entrepreneur", "ESFP": "Entertainer",
}


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
    """Return required field definitions that are empty or absent in the profile,
    excluding any field whose skip_if condition is currently met."""
    missing = []
    for field in fields:
        if not field["required"]:
            continue
        if should_skip_field(profile, field):
            continue
        if not profile.get(field["key"]):
            missing.append(field)
    return missing


def is_profile_complete(profile, fields):
    """A profile is complete when no required field is missing."""
    missing = find_missing_fields(profile, fields)
    return len(missing) == 0


def get_personality_name(mbti):
    """Map an MBTI code to its 16 Personalities name (None if not given)."""
    if not mbti:
        return None
    return PERSONALITIES.get(mbti.upper())


def derive_profile_traits(profile):
    """Look up the personality name from the optional MBTI answer."""
    return {"personality_name": get_personality_name(profile.get("mbti"))}
