"""JSON profile persistence and Google Sheets sync. No printing or domain rules."""
import json
import logging
import os
from pathlib import Path

from profile_schema import PROFILE_FIELDS

logger = logging.getLogger(__name__)


def load_profiles(path: str) -> list[dict]:
    """Load all profiles. A missing file gives []; a corrupt file is set aside."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, list):
            raise ValueError("profiles file must contain a JSON list")
        for profile in data:
            if not isinstance(profile, dict):
                raise ValueError("each profile must be a JSON object")
            if "bio" not in profile and "description" in profile:
                profile["bio"] = profile["description"]
        return data
    except (json.JSONDecodeError, ValueError, OSError) as error:
        logger.error("Could not read %s (%s); starting empty", path, error)
        _quarantine_corrupt_file(path)
        return []


def _quarantine_corrupt_file(path: str) -> None:
    """Rename an unreadable file so it is not overwritten silently."""
    try:
        os.replace(path, path + ".corrupt")
    except OSError as error:
        logger.error("Could not quarantine %s: %s", path, error)


def save_profiles(path: str, profiles: list[dict]) -> bool:
    """Write profiles atomically; deterministic key order. Returns success."""
    folder = os.path.dirname(path)
    try:
        if folder:
            os.makedirs(folder, exist_ok=True)
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(profiles, handle, indent=2, sort_keys=True, ensure_ascii=False)
        os.replace(temp_path, path)
        return True
    except OSError as error:
        logger.error("Could not save %s: %s", path, error)
        return False


def find_profile(profiles: list[dict], student_id: str) -> dict | None:
    """Return the profile with this student ID, or None."""
    for profile in profiles:
        if profile.get("student_id") == student_id:
            return profile
    return None


def filter_profiles(profiles: list[dict], key: str, value: str) -> list[dict]:
    """Return profiles whose field `key` equals `value` (case-insensitive)."""
    return [p for p in profiles if str(p.get(key, "")).lower() == value.lower()]


def upsert_profile(profiles: list[dict], profile: dict) -> list[dict]:
    """Return a new list with the profile added, replacing any same student ID."""
    others = [p for p in profiles if p.get("student_id") != profile["student_id"]]
    return others + [profile]


def sync_profile_to_sheets(profile: dict) -> tuple[bool, str]:
    """Upload one profile; preserve all sheet fields outside the profile form.

    JSON remains the local store. Import and authenticate only when syncing,
    so missing credentials or a network failure cannot prevent local saving.
    Lists display as comma-separated text; empty lists display as blank cells.
    Traits and completeness remain in the local JSON.
    """
    credentials = Path(__file__).resolve().parent / "database" / "service_account.json"
    if not credentials.is_file():
        return False, "Google Sheets sync skipped: service_account.json is missing."
    try:
        import gspread
    except ImportError:
        return False, "Google Sheets sync needs gspread: run py -m pip install gspread."

    try:
        client = gspread.service_account(filename=str(credentials))
        client.set_timeout(20)
        spreadsheet_id = os.environ.get(
            "SITOGETHER_SPREADSHEET_ID", "1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU"
        )
        worksheet = client.open_by_key(spreadsheet_id).worksheet("users")
        headers = worksheet.row_values(1)
        fields = [field["key"] for field in PROFILE_FIELDS]
        if len(headers) != len(set(headers)) or any(key not in headers for key in fields):
            return False, "Google Sheets sync stopped: users headers are missing or duplicated."
        if any(key not in profile for key in fields):
            return False, "Google Sheets sync stopped: the profile is missing form fields."
        if profile["match_preference"] not in ("Male", "Female", "Both"):
            return False, "Google Sheets sync stopped: please re-enter your match preference."

        student_id = str(profile["student_id"])
        id_column = headers.index("student_id") + 1
        matches = [
            row for row, value in enumerate(worksheet.col_values(id_column), start=1)
            if row > 1 and str(value) == student_id
        ]
        if len(matches) > 1:
            return False, "Google Sheets sync stopped: duplicate student IDs need review."

        values = {}
        for key in fields:
            value = profile[key]
            if isinstance(value, list):
                value = ", ".join(
                    str(item).strip() for item in value
                    if item is not None and str(item).strip()
                )
            elif isinstance(value, dict):
                value = json.dumps(value, ensure_ascii=False)
            values[key] = "" if value is None else str(value)

        if matches:
            # Write only owned fields, retaining Instagram and any other columns.
            from gspread.utils import rowcol_to_a1
            updates = [
                {"range": rowcol_to_a1(matches[0], headers.index(key) + 1),
                 "values": [[values[key]]]}
                for key in fields if key != "student_id"
            ]
            worksheet.batch_update(updates, value_input_option="RAW")
        else:
            worksheet.append_row(
                [values.get(header, "") for header in headers], value_input_option="RAW"
            )
        return True, "Profile synced to Google Sheets."
    except Exception as error:
        # Never print credentials, API response bodies or personal data.
        logger.warning("Google Sheets sync failed (%s)", type(error).__name__)
        return False, "Google Sheets sync failed. Your local JSON copy is safe; check access and connection."
