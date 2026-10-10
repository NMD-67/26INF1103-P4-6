"""Terminal questions and output, plus answer validation shared with Telegram."""
from datetime import date

import logic_manager

MIN_AGE = 18
MAX_AGE = 30
MAX_LIST_ITEMS = 10
MAX_ITEM_LEN = 40
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
DIGITS = "0123456789"


# ---------- output ----------
def show(message: str = ""):
    print(message)


def show_error(message):
    print(f"  [!] {message}")


def show_section(title):
    print(f"\n=== {title} ===")


# ---------- validators: (raw, field) -> (value, error) ----------
def _validate_student_id(raw, field):
    if len(raw) == 7 and raw.isdecimal():
        return raw, None
    return None, "Student ID must be exactly 7 digits."


def _validate_name(raw, field):
    error = "Name must be 2-60 letters (spaces, . ' - allowed)."
    if len(raw) < 2 or len(raw) > 60:
        return None, error
    if raw[0] not in LETTERS:
        return None, error
    for character in raw:
        if character not in LETTERS + " .'-":
            return None, error
    return " ".join(raw.split()), None


def _validate_date(raw, field):
    try:
        born = logic_manager.parse_birthday(raw)
    except ValueError:
        return None, "Use a real date in DD/MM/YYYY format."
    today = date.today()
    age = today.year - born.year
    # Subtract one if this year's birthday has not happened yet.
    if today.month < born.month:
        age -= 1
    elif today.month == born.month and today.day < born.day:
        age -= 1
    if not MIN_AGE <= age <= MAX_AGE:
        return None, f"Age must be between {MIN_AGE} and {MAX_AGE}."
    return raw, None


def _validate_choice(raw, field):
    options = field["options"]
    if raw.isdecimal() and 1 <= int(raw) <= len(options):
        return options[int(raw) - 1], None
    for option in options:
        if raw.lower() == option.lower():
            return option, None
    return None, f"Pick a number 1-{len(options)} or type one of the options."


def _validate_mbti(raw, field):
    if raw.upper() in field["options"]:
        return raw.upper(), None
    return None, "Enter one of the 16 MBTI types, e.g. INTJ."


def _validate_text(raw, field):
    if field["min_len"] <= len(raw) <= field["max_len"]:
        return raw, None
    return None, f"Must be {field['min_len']}-{field['max_len']} characters."


def _validate_telegram(raw, field):
    handle = raw.lstrip("@")
    error = "Telegram handle: 5-32 chars, letters/digits/underscore, starts with a letter."
    if len(handle) < 5 or len(handle) > 32:
        return None, error
    if handle[0] not in LETTERS:
        return None, error
    for character in handle:
        if character not in LETTERS + DIGITS + "_":
            return None, error
    return "@" + handle, None


def _validate_instagram(raw, field):
    handle = raw
    if handle.startswith("@"):
        handle = handle[1:]
    error = "Enter an Instagram username using 1-30 letters, digits, periods or underscores; not a link."
    if len(handle) < 1 or len(handle) > 30:
        return None, error
    for character in handle:
        if character not in LETTERS + DIGITS + "_.":
            return None, error
    return "@" + handle.lower(), None


def _validate_list(raw, field):
    items = []
    for part in raw.split(","):
        item = part.strip()
        if not item:
            continue
        duplicate = False
        for saved_item in items:
            if item.lower() == saved_item.lower():
                duplicate = True
                break
        if not duplicate:
            items.append(item)
    if not items:
        return None, "Enter at least one item."
    error = f"Max {MAX_LIST_ITEMS} items, each up to {MAX_ITEM_LEN} characters."
    if len(items) > MAX_LIST_ITEMS:
        return None, error
    for item in items:
        if len(item) > MAX_ITEM_LEN:
            return None, error
    return items, None


# ---------- input ----------
def validate_field(raw, field):
    """Validate one CLI or Telegram answer without prompting or printing."""
    raw = raw.strip()
    if not raw:
        if field["required"]:
            return None, "This field is required."
        if field["kind"] == "list":
            return [], None
        return None, None

    kind = field["kind"]
    if kind == "student_id":
        return _validate_student_id(raw, field)
    elif kind == "name":
        return _validate_name(raw, field)
    elif kind == "date":
        return _validate_date(raw, field)
    elif kind == "choice":
        return _validate_choice(raw, field)
    elif kind == "mbti":
        return _validate_mbti(raw, field)
    elif kind == "text":
        return _validate_text(raw, field)
    elif kind == "telegram":
        return _validate_telegram(raw, field)
    elif kind == "instagram":
        return _validate_instagram(raw, field)
    elif kind == "list":
        return _validate_list(raw, field)
    raise KeyError(kind)


def _show_options(field):
    if field["kind"] == "choice":
        for number, option in enumerate(field["options"], start=1):
            print(f"    {number}. {option}")


def ask_field(field):
    """Prompt until the answer is valid; optional fields can be skipped with Enter."""
    _show_options(field)
    suffix = ""
    if field.get("hint"):
        suffix = f" [{field['hint']}]"
    if not field["required"]:
        suffix += " (optional, Enter to skip)"
    while True:
        raw = input(f"{field['label']}{suffix}: ").strip()
        value, error = validate_field(raw, field)
        if error:
            show_error(error)
            continue
        return value


def collect_profile(fields, preset):
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
            if field["kind"] == "list":
                profile[field["key"]] = []
            else:
                profile[field["key"]] = None
            continue
        if field["section"] != current_section:
            current_section = field["section"]
            show_section(current_section)
        profile[field["key"]] = ask_field(field)
    return profile


def collect_missing(missing):
    """Re-prompt only for the required fields that are still empty."""
    show("\nSome required fields are still missing:")
    answers = {}
    for field in missing:
        answers[field["key"]] = ask_field(field)
    return answers


def confirm(question):
    """Ask a yes/no question until the answer is valid."""
    while True:
        answer = input(f"{question} (y/n): ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        show_error("Please answer y or n.")


# ---------- views ----------
def profile_label(key):
    """Turn stored field keys into readable labels, preserving acronyms."""
    labels = {
        "student_id": "Student ID", "mbti": "MBTI", "ccas": "CCAs",
        "year": "Year of Study", "events": "SIT Events", "insta_handle": "Instagram Handle",
    }
    if key in labels:
        return labels[key]
    return key.replace("_", " ").title()


def profile_value(key, value):
    """Use friendly display text without changing the stored profile value."""
    if key == "here_for" and isinstance(value, str) and value.strip().lower() == "both":
        return "Relationships and Friends"
    return _format_value(value)


def _format_value(value):
    if not value:
        return "-"
    if isinstance(value, list):
        return ", ".join(value)
    return str(value)


def show_profile_summary(profile, fields):
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
