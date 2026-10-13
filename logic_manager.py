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


# =========== Matching logic ===========

def parse_ai_matches(ai_output):
    lines = ai_output.strip().split("\n")
    matches = []

    for line in lines:
        if ":" in line and "%" in line:
            name_part, score_part = line.split(":")
            name = name_part.strip()
            score = int(score_part.strip().replace("%", ""))

            matches.append({
                "id": name,
                "score": score,
            })

    return matches

def load_matches():
    match_list = []
    try:
        file = open("Matching/Sample_score.txt", "r")
        lines = file.readlines()

        for line in lines:
            line = line.strip()

            if line != "":
                parts = line.split(":")

                if len(parts) == 2:
                    student_id = parts[0]
                    score = int(parts[1].replace("%", ""))

                    match_list.append([student_id, score])
        file.close()

    except FileNotFoundError:
        print("file not found")

    return match_list