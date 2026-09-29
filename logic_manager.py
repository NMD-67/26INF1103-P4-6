"""Domain logic for profiles: completeness checks and derived traits.

No printing, no file access, no API calls.
"""
from datetime import date, datetime

STEMS = ["Jia", "Yi", "Bing", "Ding", "Wu", "Ji", "Geng", "Xin", "Ren", "Gui"]
BRANCHES = ["Zi", "Chou", "Yin", "Mao", "Chen", "Si", "Wu", "Wei", "Shen", "You", "Xu", "Hai"]
ANIMALS = ["Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
           "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig"]
ELEMENTS = ["Wood", "Wood", "Fire", "Fire", "Earth", "Earth", "Metal", "Metal", "Water", "Water"]

# (month, day) on which each Western sign starts; Capricorn wraps the year end.
WESTERN_SIGNS = [
    ((1, 20), "Aquarius"), ((2, 19), "Pisces"), ((3, 21), "Aries"), ((4, 20), "Taurus"),
    ((5, 21), "Gemini"), ((6, 21), "Cancer"), ((7, 23), "Leo"), ((8, 23), "Virgo"),
    ((9, 23), "Libra"), ((10, 23), "Scorpio"), ((11, 22), "Sagittarius"), ((12, 22), "Capricorn"),
]

# Approximate solar-term starts: (month, day) -> month index (0 = Yin/Tiger month).
BAZI_MONTH_STARTS = [
    ((1, 6), 11), ((2, 4), 0), ((3, 6), 1), ((4, 5), 2), ((5, 6), 3), ((6, 6), 4),
    ((7, 7), 5), ((8, 8), 6), ((9, 8), 7), ((10, 8), 8), ((11, 7), 9), ((12, 7), 10),
]

# Known Jia-Zi (index 0) day, used to compute the day pillar.
JIAZI_REFERENCE_DAY = date(1949, 10, 1)

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


def get_western_zodiac(birthday: date) -> str:
    """Return the Western zodiac sign for a birthday."""
    md = (birthday.month, birthday.day)
    sign = "Capricorn"  # anything before 20 Jan falls into the wrapped sign
    for start, name in WESTERN_SIGNS:
        if md >= start:
            sign = name
    return sign


def _bazi_year(birthday: date) -> int:
    """Ba Zi years change at Li Chun (~4 Feb), not on 1 Jan."""
    return birthday.year - 1 if (birthday.month, birthday.day) < (2, 4) else birthday.year


def _bazi_month_index(birthday: date) -> int:
    """Month index 0-11 where 0 is the Yin (Tiger) month starting ~4 Feb."""
    md = (birthday.month, birthday.day)
    if md < (1, 6):
        return 10  # early January still belongs to the Zi month
    index = 11
    for start, month_index in BAZI_MONTH_STARTS:
        if md >= start:
            index = month_index
    return index


def _pillar(stem: int, branch: int) -> str:
    return f"{STEMS[stem % 10]}-{BRANCHES[branch % 12]}"


def calculate_bazi(birthday: date) -> dict:
    """Compute year, month and day pillars, the Chinese zodiac and the day master.

    Hour pillar is skipped because birth time is not collected; month
    boundaries are approximate solar-term dates (can be off by a day).
    """
    year = _bazi_year(birthday)
    year_stem, year_branch = (year - 4) % 10, (year - 4) % 12

    month_index = _bazi_month_index(birthday)
    month_stem = (year_stem % 5) * 2 + 2 + month_index
    month_branch = month_index + 2

    day_index = (birthday - JIAZI_REFERENCE_DAY).days % 60
    day_stem, day_branch = day_index % 10, day_index % 12

    polarity = "Yang" if day_stem % 2 == 0 else "Yin"
    return {
        "chinese_zodiac": ANIMALS[year_branch],
        "year_pillar": _pillar(year_stem, year_branch),
        "month_pillar": _pillar(month_stem, month_branch),
        "day_pillar": _pillar(day_stem, day_branch),
        "day_master": f"{polarity} {ELEMENTS[day_stem]}",
    }


def get_personality_name(mbti: str | None) -> str | None:
    """Map an MBTI code to its 16 Personalities name (None if not given)."""
    if not mbti:
        return None
    return PERSONALITIES.get(mbti.upper())


def derive_profile_traits(profile: dict) -> dict:
    """Build all derived fields stored alongside the profile."""
    birthday = parse_birthday(profile["birthday"])
    traits = {"western_zodiac": get_western_zodiac(birthday)}
    traits.update(calculate_bazi(birthday))
    traits["personality_name"] = get_personality_name(profile.get("mbti"))
    return traits