"""Existing profile logic exposed through the ProfileLogicManager class."""

from datetime import datetime
from .profile_logic_manager import ProfileLogicManager

_profile_logic = ProfileLogicManager()


def parse_birthday(text):
    """Convert a DD/MM/YYYY string to a date (original behaviour)."""
    return datetime.strptime(text, "%d/%m/%Y").date()


def should_skip_field(profile, field):
    return _profile_logic.should_skip_field(profile, field)


def find_missing_fields(profile, fields):
    return _profile_logic.find_missing_fields(profile, fields)


def is_profile_complete(profile, fields):
    return _profile_logic.is_profile_complete(profile, fields)


def clear_field(profile, field):
    return _profile_logic.clear_field(profile, field)


def validate_age_preferences(profile):
    return _profile_logic.validate_age_preferences(profile)


def calculate_age(birthday, today=None):
    return _profile_logic.calculate_age(birthday, today=today)

def calculate_horoscope(birthday):
    return _profile_logic.calculate_horoscope(birthday)

def process_birthday(text, today=None):
    return _profile_logic.process_birthday(text, today=today)
