"""Shared profile questions, validation settings and repository mappings.

PROFILE_FIELDS is generated for the existing CLI, Telegram and Sheets code.
storage is the PostgreSQL table, or None when that mapping is not yet configured.
Google Sheets continues to use the form keys in PROFILE_FIELDS.
"""

SECTION_BACKGROUND = "Background Information"
SECTION_PERSONAL = "Personal Information"
SECTION_EXTRA = "Extracurricular"

RACES = ["Chinese", "Malay", "Indian", "Eurasian", "Other"]

RELIGIONS = [
    "Buddhism",
    "Christianity",
    "Catholicism",
    "Islam",
    "Hinduism",
    "Taoism",
    "Sikhism",
    "Free thinker",
    "No religion",
    "Others",
]

SIT_COURSES = [
    "Accountancy",
    "Aircraft Systems Engineering",
    "Applied Artificial Intelligence",
    "Applied Computing",
    "Applied Computing (Fintech)",
    "Applied Computing Degree (via CSM Pathway)",
    "Aviation Management",
    "Business and Infocomm Technology",
    "Chemical Engineering",
    "Civil Engineering",
    "Communication and Digital Media",
    "Computer Engineering",
    "Computer Science in Interactive Media and Game Development",
    "Computer Science in Real-Time Interactive Simulation",
    "Computing Science",
    "Diagnostic Radiography",
    "Dietetics and Nutrition",
    "Digital Supply Chain",
    "Electrical and Electronic Engineering",
    "Electrical and Electronic Engineering Degree (via CSM Pathway)",
    "Electrical Power Engineering",
    "Electronics and Data Engineering",
    "Engineering Systems",
    "Food Business Management (Baking and Pastry Arts)",
    "Food Business Management (Culinary Arts)",
    "Food Technology",
    "Hospitality and Tourism Management",
    "Information and Communications Technology (Information Security)",
    "Information and Communications Technology (Software Engineering)",
    "Mechanical Design and Manufacturing Engineering",
    "Mechanical Engineering",
    "Naval Architecture and Marine Engineering",
    "Nursing",
    "Occupational Therapy",
    "Pharmaceutical Engineering",
    "Physiotherapy",
    "Physiotherapy (Top-Up)",
    "Radiation Therapy",
    "Robotics Systems",
    "Speech and Language Therapy",
    "Sustainable Built Environment",
    "User Experience and Game Design",
]

MBTI_TYPES = [
    "INTJ",
    "INTP",
    "ENTJ",
    "ENTP",
    "INFJ",
    "INFP",
    "ENFJ",
    "ENFP",
    "ISTJ",
    "ISFJ",
    "ESTJ",
    "ESFJ",
    "ISTP",
    "ISFP",
    "ESTP",
    "ESFP",
]

# Dictionary order controls the order of questions.
# form_key preserves existing form/Sheets names where PostgreSQL uses another name.
from models.dealbreaker import DealBreaker
from models.profile import Profile
from dataclasses import is_dataclass

USER_FIELD_CONFIG = {
    "student_id": {
        "editable": False,
        "storage": "users",
        "type": str,
        "question": "What is your student ID?",
        "label": "Student ID",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "student_id",
        "hint": "7 digits, e.g. 2500123",
    },
    "name": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your name?",
        "label": "Name",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "name",
    },
    "birthday": {
        "editable": True,
        "storage": None,
        "type": str,
        "question": "When is your birthday?",
        "label": "Birthday",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "date",
        "hint": "DD/MM/YYYY",
    },
    # Derived from the birthday locally and saved; not asked as separate questions.
    "age": {
        "editable": True,
        "storage": "users",
        "type": int,
        "derived": True,
    },
    "horoscope": {
        "editable": True,
        "storage": "users",
        "type": str,
        "derived": True,
    },
    "gender": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your gender?",
        "label": "Gender",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": ["Male", "Female", "Other"],
    },
    "year": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "Which year of study are you in?",
        "label": "Year of Study",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": ["1", "2", "3", "4"],
    },
    "course": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "Which course are you studying?",
        "label": "Course",
        "section": SECTION_BACKGROUND,
        "required": True,
        "kind": "choice",
        "options": SIT_COURSES,
    },
    "bio": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What would you like others to know about you?",
        "label": "Bio",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "text",
        "min_len": 1,
        "max_len": 300,
        "hint": "max 300 characters; Tell us more about yourself",
    },
    "race": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your race?",
        "label": "Race",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "choice",
        "options": RACES + ["Prefer not to say"],
    },
    "religion": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your religion?",
        "label": "Religion",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "choice",
        "options": RELIGIONS + ["Prefer not to say"],
    },
    "mbti": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your MBTI personality type?",
        "label": "MBTI",
        "section": SECTION_BACKGROUND,
        "required": False,
        "kind": "mbti",
        "options": MBTI_TYPES,
        "hint": "e.g. INTJ",
    },
    "match_preference": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "Who would you like to be matched with?",
        "label": "Match Preference",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "choice",
        "options": ["Male", "Female", "Both"],
        "class": "dealbreakers",
    },
    "race_preference": {
        "editable": True,
        "storage": None,
        "type": str,
        "question": "Do you have a race preference for your matches?",
        "label": "Race Preference",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "choice",
        "options": ["No preference"] + RACES + ["Prefer not to say"],
        "class": "dealbreakers",
        "key": "race",
    },
    "religion_preference": {
        "editable": True,
        "storage": None,
        "type": str,
        "question": "Do you have a religion preference for your matches?",
        "label": "Religion Preference",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "choice",
        "options": ["No preference"] + RELIGIONS,
        "class": "dealbreakers",
        "key": "religion",
    },
    "min_age": {
        "editable": True,
        "storage": None,
        "type": str,
        "question": "What is the youngest age you would like to match with?",
        "label": "Minimum Preferred Age",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "age",
        "hint": "18-30; Enter for no minimum preference",
        "class": "dealbreakers",
        "key": "min_age",
    },
    "max_age": {
        "editable": True,
        "storage": None,
        "type": str,
        "question": "What is the oldest age you would like to match with?",
        "label": "Maximum Preferred Age",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "age",
        "hint": "18-30; Enter for no maximum preference",
        "class": "dealbreakers",
        "key": "max_age",
    },
    "here_for": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "Are you here for friendship, a relationship, or both?",
        "label": "Here for",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "choice",
        "options": ["Friends", "Relationship", "Both"],
    },
    "expectations": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What are you looking for in a relationship?",
        "label": "Expectations in Relationships",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "text",
        "min_len": 10,
        "max_len": 500,
        "hint": "10-500 characters",
        "skip_if": {"field": "here_for", "in": ["Friends"]},
    },
    "tele_handle": {
        "editable": True,
        "storage": "users",
        "type": str,
        "form_key": "telegram_handle",
        "question": "What is your Telegram handle?",
        "label": "Telegram handle",
        "section": SECTION_PERSONAL,
        "required": True,
        "kind": "telegram",
        "hint": "only shared once you match",
    },
    "insta_handle": {
        "editable": True,
        "storage": "users",
        "type": str,
        "question": "What is your Instagram handle?",
        "label": "Instagram Handle",
        "section": SECTION_PERSONAL,
        "required": False,
        "kind": "instagram",
        "hint": "Username only, with or without @; optional",
    },
    "ccas": {
        "editable": True,
        "storage": "ccas",
        "type": list,
        "column_name": "cca",
        "question": "Which CCAs are you currently involved in at SIT?",
        "label": "CCAs",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },
    "events": {
        "editable": True,
        "storage": "events",
        "type": list,
        "column_name": "event",
        "question": "Which SIT events have you participated in?",
        "label": "SIT Events",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },
    "hobbies": {
        "editable": True,
        "storage": "hobbies",
        "type": list,
        "column_name": "hobby",
        "question": "What are your hobbies?",
        "label": "Hobbies",
        "section": SECTION_EXTRA,
        "required": True,
        "kind": "list",
        "hint": "comma-separated, at least one",
    },
    "interest_groups": {
        "editable": True,
        "storage": "interests",
        "type": list,
        "column_name": "interest",
        "form_key": "interest_groups",
        "model_key": "interest_groups",
        "question": "Which interest groups do you belong to outside SIT?",
        "label": "Outside Interest Groups",
        "section": SECTION_EXTRA,
        "required": False,
        "kind": "list",
        "hint": "comma-separated",
    },
    "dealbreakers": {
        "storage": "dealbreakers",
        "label": "Deal Breakers",
        "type": DealBreaker,
        "exclusive_to": Profile,
    },
}

# This is a generated view, not a second handwritten schema.
PROFILE_FIELDS = [
    {"key": settings.get("form_key", key), **settings}
    for key, settings in USER_FIELD_CONFIG.items()
    if not settings.get("derived", False)
]

# Do not make existing SQL queries request columns that have not been migrated yet.
REPOSITORY_FIELD_CONFIG = {
    key: settings
    for key, settings in USER_FIELD_CONFIG.items()
    if settings["storage"] is not None
}

SCALAR_FIELDS = [
    key
    for key, settings in REPOSITORY_FIELD_CONFIG.items()
    if settings["type"] != list and settings["type"] != DealBreaker
]
LIST_FIELDS = [
    key for key, settings in REPOSITORY_FIELD_CONFIG.items() if settings["type"] == list
]

CLASS_FIELDS = ["dealbreakers"]

DEAL_BREAKER_CONFIG = {"min_age", "max_age", "religion", "race", "gender"}
