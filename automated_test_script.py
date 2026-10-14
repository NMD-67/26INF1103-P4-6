import runpy
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FAKE_OTP = "1234"

# Hardcoded candidate profiles that "the AI" will recommend.
# Adjust the keys to match your PROFILE_FIELDS if save_profile rejects them.
FAKE_SCORES = {"2500001": 0.92, "2500002": 0.75, "2500003": 0.55}

FAKE_CANDIDATES = [
    {
        "student_id": "2500001", "name": "Alice Tan", "year": 1,
        "course": "Applied AI", "bio": "Loves hackathons and bubble tea.",
        "here_for": ["Friends", "Study buddies"], "hobbies": ["Gaming", "Hiking"],
        "profile_complete": True,
    },
    {
        "student_id": "2500002", "name": "Ben Lim", "year": 2,
        "course": "Computer Science", "bio": "Gym, coffee, and code.",
        "here_for": ["Friends"], "hobbies": ["Gym", "Coffee"],
        "profile_complete": True,
    },
    {
        "student_id": "2500003", "name": "Chloe Ng", "year": 1,
        "course": "Digital Supply Chain", "bio": "Always down for supper runs.",
        "here_for": ["Study buddies"], "hobbies": ["Cooking", "Anime"],
        "profile_complete": True,
    },
]


# ---------------------------------------------------------------- fake AI --
def _seed_candidates(student_id):
    """Put the fake candidates into the real db / recommendation list."""
    from database import db
    from src import matches

    for p in FAKE_CANDIDATES:
        try:
            if not db.get_profile(p["student_id"]):
                db.save_profile(dict(p))
        except Exception as e:
            print(f"Could not seed profile {p['student_id']}: {e}")

    # Add to the recommendation list. Function name is a guess - rename to
    # whatever your src/matches.py actually exposes.
    # db.add_to_recco_student_id expects {student_id: compatibility_score}.
    # Scores are 0-1 here; if your compatibility_label() expects 0-100,
    # multiply them.
    scores = dict(FAKE_SCORES)
    for name in ("add_recco_student_id", "add_recco_student_ids",
                 "save_recco_list", "set_recco_list"):
        fn = getattr(matches, name, None)
        if fn:
            try:
                fn(student_id, scores)
                return True
            except Exception as e:
                print(f"matches.{name} failed: {e}")
    print("No matches")
    return False


fake_profile_matching = types.ModuleType("profile_matching_AI")


def _populate_recco_list(student_id):
    return {"success": _seed_candidates(student_id)}


fake_profile_matching.populate_recco_list = _populate_recco_list


fake_matchmaking = types.ModuleType("matchmaking_ai")


def _fake_result(yours, theirs):
    return {
        "name": theirs.get("name", "Unknown"),
        "student_id": theirs.get("student_id"),
        "suggestions": [
            "Grab bubble tea at the campus canteen.",
            "Start a study session for your shared modules.",
            "Ask about their favourite hobby to break the ice.",
        ],
    }


def _prepare_connection(yours, theirs):
    return _fake_result(yours, theirs)


def _format_recommendations(result):
    lines = [f"Connection: {result.get('name')}"]
    lines += [f"  - {s}" for s in result.get("suggestions", [])]
    return "\n".join(lines)


async def _get_matches_for_user_async(student_id):
    return [_fake_result({}, p) for p in FAKE_CANDIDATES[:2]]


fake_matchmaking.prepare_connection = _prepare_connection
fake_matchmaking.format_recommendations = _format_recommendations
fake_matchmaking.get_matches_for_user_async = _get_matches_for_user_async

# Must be registered BEFORE main.py runs its imports.
sys.modules["profile_matching_AI"] = fake_profile_matching
sys.modules["matchmaking_ai"] = fake_matchmaking


# --------------------------------------------------------------- fake auth --
from src import auth  # noqa: E402  (real module, then patch network parts)


async def _login_user(student_id):
    print(f"OTP 'sent'. Use: {FAKE_OTP}")
    return 200


def _validate_otp(student_id, otp):
    return 200 if otp == FAKE_OTP else 403


auth.login_user = _login_user
auth.validate_otp = _validate_otp


# -------------------------------------------------------------------- run --
if __name__ == "__main__":
    runpy.run_path(str(HERE / "main.py"), run_name="__main__")