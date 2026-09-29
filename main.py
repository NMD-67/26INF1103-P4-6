"""Entry point: profile setup flow (io -> logic -> data)."""
from database import db
import io_manager
import logic_manager
from profile_schema import PROFILE_FIELDS



def get_field(key: str) -> dict:
    """Look up a field definition by key."""
    for field in PROFILE_FIELDS:
        if field["key"] == key:
            return field
    raise ValueError(f"Unknown profile field: {key}")


def run_profile_setup() -> None:
    io_manager.show("SITogether - Profile Setup")

    student_id = io_manager.ask_field(get_field("student_id"))
    try:
        existing = db.load_profile(student_id)
    except Exception:
        io_manager.show_error("Could not read your profile. Check your connection and try again.")
        return
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
        result = db.save_profile(profile)
        if result["saved"]:
            io_manager.show("Profile saved.")
        else:
            io_manager.show_error(result["message"])
    else:
        io_manager.show("Profile discarded.")


if __name__ == "__main__":
    run_profile_setup()
