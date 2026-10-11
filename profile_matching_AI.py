"""
AI Profile Matching
--------------------
Scores compatibility between a given main user and every other user via
the Groq API, and writes the results back to the "matches" tab.

"""

import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def get_groq_client():
    api_key = os.getenv("PROFILE_MATCHING_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing Groq API key. Set PROFILE_MATCHING_API_KEY or GROQ_API_KEY."
        )
    return Groq(api_key=api_key)

# Fields for the AI to analyse
FIELDS_FOR_AI = [
    "birthday", "gender", "course", "bio", "religion", "mbti",
    "match_preference", "here_for", "expectations", "ccas",
    "events", "hobbies", "interest_groups"
]

def filter_profile_fields(profile):
    """Keep only the allowlisted fields before sending a profile to the AI."""
    return {field: profile.get(field, "") for field in FIELDS_FOR_AI}

# Call GROQ AI to get a compatibility score for a pair of profiles
def get_compatibility_score(client, main_profile, candidate_profile):
    """Calls the AI once for ONE pair of profiles. Returns an int 0-100,
    or None if the call or validation failed."""

    instructions = (
        "You compare two user dating/matching profiles and return a single "
        "compatibility score from 0 to 100, based on shared interests, "
        "lifestyle, and stated preferences. "
        "Respond ONLY with valid JSON in this exact format, no other text: "
        '{"score": <integer 0-100>}'
    )

    payload = {
        "profile_a": filter_profile_fields(main_profile),
        "profile_b": filter_profile_fields(candidate_profile)
    }

    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            max_completion_tokens=1024,
            reasoning_effort="low",
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": json.dumps(payload)}
            ]
        )

        raw = response.choices[0].message.content.strip()
        parsed = json.loads(raw)
        score = parsed["score"]

        if not isinstance(score, (int, float)) or not (0 <= score <= 100):
            raise ValueError(f"Score out of range: {score}")

        return int(score)

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Validation failed for candidate {candidate_profile.get('student_id')}: {e}")
        return None
    except Exception as e:
        print(f"API call failed for candidate {candidate_profile.get('student_id')}: {e}")
        return None

# Compare main user profile with all other profiles and return a sorted list of results
from database.db import read_profile, get_sheet
USERS_TAB = "users"
MATCHES_TAB = "matches"
 
def AI_Profile_Matching(User_ID, groq_client):
    # read_profile already handles "not found" (returns None) and
    # "duplicate ids" (raises ValueError) for us.
    main_profile = read_profile(User_ID, sheet_name=USERS_TAB)

    if main_profile is None:
        print(f"User {User_ID} not found in {USERS_TAB}")
        return []

    worksheet = get_sheet(USERS_TAB)
    all_profiles = worksheet.get_all_records()
    candidates = [p for p in all_profiles if str(p["student_id"]) != str(User_ID)]

    results = []
    for candidate in candidates:
        score = get_compatibility_score(groq_client, main_profile, candidate)
        if score is not None:
            results.append({
                "user_id": candidate["student_id"],
                "name": candidate["name"],
                "score": score
            })

    results.sort(key=lambda r: r["score"], reverse=True)
    return results

# Append to recco_student_id
from database.db import add_to_recco_student_id

def Add_To_Database(User_ID, results):
    if not results:
        print("No results to save.")
        return None

    # String keys, so they match the keys already stored in the sheet
    new_students = {str(r["user_id"]): r["score"] for r in results}

    outcome = add_to_recco_student_id(User_ID, new_students)

    print("DEBUG outcome:", type(outcome), outcome)   # remove once you know what it returns

    if isinstance(outcome, dict):
        ok = outcome.get("success", False)
        error = outcome.get("error")
    else:
        ok = bool(outcome)       # guess: 0 = failure, anything else = success
        error = outcome

    if not ok:
        print(f"Failed to add recco_student_id for {User_ID}: {error}")

    return outcome

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
 
if __name__ == "__main__":
    USER_ID = 1001  # <-- set the main user to match

    groq_client = get_groq_client()

    results = AI_Profile_Matching(USER_ID, groq_client)
    Add_To_Database(USER_ID, results)

    # For inspection only - not written to the sheet
    name_score = {r["name"]: r["score"] for r in results}
    print(name_score)