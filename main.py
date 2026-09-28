"""Entry point: profile setup flow (io -> logic -> data)."""
import os

import data_manager
import io_manager
import logic_manager
from profile_schema import PROFILE_FIELDS

DATA_PATH = os.environ.get("SITOGETHER_DATA", "data/profiles.json")


def get_field(key: str) -> dict:
    """Look up a field definition by key."""
    return next(f for f in PROFILE_FIELDS if f["key"] == key)


def run_profile_setup() -> None:
    profiles = data_manager.load_profiles(DATA_PATH)
    io_manager.show("SITogether - Profile Setup")

    student_id = io_manager.ask_field(get_field("student_id"))
    existing = data_manager.find_profile(profiles, student_id)
    if existing and not io_manager.confirm("A profile already exists for this ID. Overwrite it?"):
        io_manager.show_profile_summary(existing, PROFILE_FIELDS)
        return

    profile = io_manager.collect_profile(PROFILE_FIELDS, {"student_id": student_id})

    missing = logic_manager.find_missing_fields(profile, PROFILE_FIELDS)
    while missing:
        profile.update(io_manager.collect_missing(missing))
        missing = logic_manager.find_missing_fields(profile, PROFILE_FIELDS)

    profile["traits"] = logic_manager.derive_profile_traits(profile)
    profile["profile_complete"] = logic_manager.is_profile_complete(profile, PROFILE_FIELDS)

    io_manager.show_profile_summary(profile, PROFILE_FIELDS)
    if io_manager.confirm("\nSave this profile?"):
        saved = data_manager.save_profiles(DATA_PATH, data_manager.upsert_profile(profiles, profile))
        io_manager.show("Profile saved." if saved else "Could not save the profile.")
        if saved:
            synced, message = data_manager.sync_profile_to_sheets(profile)
            if synced:
                io_manager.show(message)
            else:
                io_manager.show_error(message)
    else:
        io_manager.show("Profile discarded.")


if __name__ == "__main__":
    run_profile_setup()
