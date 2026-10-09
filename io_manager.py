"""All user interaction. Every print() and input() in the project lives here."""
import re
from datetime import date

import logic_manager

MIN_AGE, MAX_AGE = 18, 30
MAX_LIST_ITEMS, MAX_ITEM_LEN = 10, 40


# ---------- output ----------
def show(message: str = "") -> None:
    print(message)


def show_error(message: str) -> None:
    print(f"  [!] {message}")


def show_section(title: str) -> None:
    print(f"\n=== {title} ===")


# ---------- validators: (raw, field) -> (value, error) ----------
def _validate_student_id(raw: str, field: dict) -> tuple:
    if re.fullmatch(r"\d{7}", raw):
        return raw, None
    return None, "Student ID must be exactly 7 digits."


def _validate_name(raw: str, field: dict) -> tuple:
    if re.fullmatch(r"[A-Za-z][A-Za-z .'\-]{1,59}", raw):
        return " ".join(raw.split()), None
    return None, "Name must be 2-60 letters (spaces, . ' - allowed)."


def _validate_date(raw: str, field: dict) -> tuple:
    try:
        born = logic_manager.parse_birthday(raw)
    except ValueError:
        return None, "Use a real date in DD/MM/YYYY format."
    today = date.today()
    age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
    if not MIN_AGE <= age <= MAX_AGE:
        return None, f"Age must be between {MIN_AGE} and {MAX_AGE}."
    return raw, None


def _validate_choice(raw: str, field: dict) -> tuple:
    options = field["options"]
    if raw.isdigit() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1], None
    for option in options:
        if raw.lower() == option.lower():
            return option, None
    return None, f"Pick a number 1-{len(options)} or type one of the options."


def _validate_mbti(raw: str, field: dict) -> tuple:
    if raw.upper() in field["options"]:
        return raw.upper(), None
    return None, "Enter one of the 16 MBTI types, e.g. INTJ."


def _validate_text(raw: str, field: dict) -> tuple:
    if field["min_len"] <= len(raw) <= field["max_len"]:
        return raw, None
    return None, f"Must be {field['min_len']}-{field['max_len']} characters."


def _validate_telegram(raw: str, field: dict) -> tuple:
    handle = raw.lstrip("@")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{4,31}", handle):
        return "@" + handle, None
    return None, "Telegram handle: 5-32 chars, letters/digits/underscore, starts with a letter."


def _validate_instagram(raw: str, field: dict) -> tuple:
    handle = raw.removeprefix("@")
    if re.fullmatch(r"[A-Za-z0-9_.]{1,30}", handle):
        return "@" + handle.lower(), None
    return None, "Enter an Instagram username using 1-30 letters, digits, periods or underscores; not a link."


def _validate_list(raw: str, field: dict) -> tuple:
    items = []
    for part in raw.split(","):
        item = part.strip()
        if item and item.lower() not in [i.lower() for i in items]:
            items.append(item)
    if not items:
        return None, "Enter at least one item."
    if len(items) > MAX_LIST_ITEMS or any(len(i) > MAX_ITEM_LEN for i in items):
        return None, f"Max {MAX_LIST_ITEMS} items, each up to {MAX_ITEM_LEN} characters."
    return items, None


VALIDATORS = {
    "student_id": _validate_student_id, "name": _validate_name, "date": _validate_date,
    "choice": _validate_choice, "mbti": _validate_mbti, "text": _validate_text,
    "instagram": _validate_instagram, "telegram": _validate_telegram, "list": _validate_list,
}


# ---------- input ----------
def validate_field(raw: str, field: dict) -> tuple:
    """Validate one CLI or Telegram answer without prompting or printing."""
    raw = raw.strip()
    if not raw:
        if field["required"]:
            return None, "This field is required."
        return ([] if field["kind"] == "list" else None), None
    return VALIDATORS[field["kind"]](raw, field)


def _show_options(field: dict) -> None:
    if field["kind"] == "choice":
        for number, option in enumerate(field["options"], start=1):
            print(f"    {number}. {option}")


def ask_field(field: dict):
    """Prompt until the answer is valid; optional fields can be skipped with Enter."""
    _show_options(field)
    suffix = f" [{field['hint']}]" if field.get("hint") else ""
    if not field["required"]:
        suffix += " (optional, Enter to skip)"
    while True:
        raw = input(f"{field['label']}{suffix}: ").strip()
        value, error = validate_field(raw, field)
        if error:
            show_error(error)
            continue
        return value


def collect_profile(fields: list[dict], preset: dict) -> dict:
    """Ask every field not already in `preset`, grouped by section.

    A field whose skip_if condition is met by earlier answers is set to an
    empty value (None, or [] for list fields) without being asked at all.
    """
    profile = dict(preset)
    current_section = None
    for field in fields:
        if field["key"] in profile:
            continue
        if logic_manager.should_skip_field(profile, field):
            profile[field["key"]] = [] if field["kind"] == "list" else None
            continue
        if field["section"] != current_section:
            current_section = field["section"]
            show_section(current_section)
        profile[field["key"]] = ask_field(field)
    return profile


def collect_missing(missing: list[dict]) -> dict:
    """Re-prompt only for the required fields that are still empty."""
    show("\nSome required fields are still missing:")
    return {field["key"]: ask_field(field) for field in missing}


def confirm(question: str) -> bool:
    """Ask a yes/no question until the answer is valid."""
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        show_error("Please answer y or n.")


# ---------- views ----------
def profile_label(key: str) -> str:
    if key == "insta_handle":
        return "Instagram Handle"
    """Turn stored field keys into readable labels, preserving acronyms."""
    labels = {
        "student_id": "Student ID", "mbti": "MBTI", "ccas": "CCAs",
        "year": "Year of Study", "events": "SIT Events", "insta_handle": "Instagram Handle",
    }
    return labels.get(key, key.replace("_", " ").title())


def profile_value(key: str, value) -> str:
    """Use friendly display text without changing the stored profile value."""
    if key == "here_for" and isinstance(value, str) and value.strip().lower() == "both":
        return "Relationships and Friends"
    return _format_value(value)


def _format_value(value) -> str:
    if isinstance(value, list):
        return ", ".join(value) if value else "-"
    return str(value) if value else "-"


def show_profile_summary(profile: dict, fields: list[dict]) -> None:
    """Print the profile grouped by section, followed by the MBTI personality name."""
    current_section = None
    for field in fields:
        if field["section"] != current_section:
            current_section = field["section"]
            show_section(current_section)
        show(f"  {field['label']}: {_format_value(profile.get(field['key']))}")
    traits = profile.get("traits", {})
    show_section("Personality")
    show(f"  16 Personalities: {traits.get('personality_name') or '-'}")
