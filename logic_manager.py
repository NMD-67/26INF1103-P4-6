"""Domain logic for profiles: completeness checks and MBTI personality names.

No printing, no file access, no API calls.
"""
from datetime import date, datetime

PERSONALITIES = {
    "INTJ": "Architect", "INTP": "Logician", "ENTJ": "Commander", "ENTP": "Debater",
    "INFJ": "Advocate", "INFP": "Mediator", "ENFJ": "Protagonist", "ENFP": "Campaigner",
    "ISTJ": "Logistician", "ISFJ": "Defender", "ESTJ": "Executive", "ESFJ": "Consul",
    "ISTP": "Virtuoso", "ISFP": "Adventurer", "ESTP": "Entrepreneur", "ESFP": "Entertainer",
}


def parse_birthday(text: str) -> date:
    """Convert a DD/MM/YYYY string to a date."""
    return datetime.strptime(text, "%d/%m/%Y").date()


def should_skip_field(profile: dict, field: dict) -> bool:
    """Return True if this field's skip_if condition is met by earlier answers."""
    condition = field.get("skip_if")
    if not condition:
        return False
    return profile.get(condition["field"]) in condition["in"]


def find_missing_fields(profile: dict, fields: list[dict]) -> list[dict]:
    """Return required field definitions that are empty or absent in the profile,
    excluding any field whose skip_if condition is currently met."""
    return [
        f for f in fields
        if f["required"] and not profile.get(f["key"]) and not should_skip_field(profile, f)
    ]


def is_profile_complete(profile: dict, fields: list[dict]) -> bool:
    """A profile is complete when no required field is missing."""
    return not find_missing_fields(profile, fields)


def get_personality_name(mbti: str | None) -> str | None:
    """Map an MBTI code to its 16 Personalities name (None if not given)."""
    if not mbti:
        return None
    return PERSONALITIES.get(mbti.upper())


def derive_profile_traits(profile: dict) -> dict:
    """Look up the personality name from the optional MBTI answer."""
    return {"personality_name": get_personality_name(profile.get("mbti"))}
