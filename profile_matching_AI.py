"""
AI Profile Matching
--------------------
Scores compatibility between a given main user and every other user via
the Groq API, and writes the results back to the "matches" tab.

"""

import os
import json
import math
import time
import logging

import groq
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
 
def get_groq_client():
    api_key = os.getenv("PROFILE_MATCHING_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key or not api_key.strip():
        raise RuntimeError(
            "Missing Groq API key. Set PROFILE_MATCHING_API_KEY or GROQ_API_KEY."
        )
    try:
        return Groq(api_key=api_key.strip(), timeout=30.0)
    except Exception as e:
        raise RuntimeError(f"Failed to create Groq client: {e}") from e

# Fields for the AI to analyse
FIELDS_FOR_AI = [
    "birthday", "gender", "course", "bio", "religion", "mbti",
    "match_preference", "here_for", "expectations", "ccas",
    "events", "hobbies", "interest_groups"
]

# Allow only the fields we want to send to the AI, and fill in missing fields with empty strings
def filter_profile_fields(profile):
    if not isinstance(profile, dict):
        raise ValueError(f"Profile must be a dict, got {type(profile).__name__}")
    return {field: profile.get(field, "") for field in FIELDS_FOR_AI}

# Call GROQ AI to get a compatibility score for a pair of profiles
def get_compatibility_score(client, main_profile, candidate_profile):
    """Calls the AI for ONE pair of profiles. Returns an int 0-100,
    or None if the call or validation failed. Never raises."""

    max_attempts = 3  # 1 initial try + 2 retries

    candidate_id = (
        candidate_profile.get("student_id")
        if isinstance(candidate_profile, dict) else "<unknown>"
    )

    if client is None:
        logger.error("No Groq client supplied; cannot score candidate %s", candidate_id)
        return None

    instructions = (
        "You compare two user dating/matching profiles and return a single "
        "compatibility score from 0 to 100, based on shared interests, "
        "lifestyle, and stated preferences. "
        "Respond ONLY with valid JSON in this exact format, no other text: "
        '{"score": <integer 0-100>}'
    )

    # Build the prompt. If this fails, retrying won't help, so skip the record.
    try:
        payload = {
            "profile_a": filter_profile_fields(main_profile),
            "profile_b": filter_profile_fields(candidate_profile)
        }
        # default=str so dates / odd sheet values can't break json.dumps
        user_content = json.dumps(payload, default=str)
    except (ValueError, TypeError) as e:
        logger.warning("Skipping candidate %s: bad profile data: %s", candidate_id, e)
        return None
    except Exception:
        logger.exception("Unexpected error building prompt for candidate %s", candidate_id)
        return None

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                max_completion_tokens=1024,
                reasoning_effort="low",
                response_format={"type": "json_object"},
                temperature=0,
                messages=[
                    {"role": "system", "content": instructions},
                    {"role": "user", "content": user_content}
                ]
            )

            # --- Validate the response (any failure raises ValueError -> retry) ---
            choices = getattr(response, "choices", None)
            if not choices:
                raise ValueError("Response contained no choices")

            choice = choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                raise ValueError("Response truncated (hit token limit)")

            raw = getattr(getattr(choice, "message", None), "content", None)
            if not isinstance(raw, str) or not raw.strip():
                raise ValueError("Response content was empty")

            try:
                parsed = json.loads(raw.strip())
            except json.JSONDecodeError as e:
                raise ValueError(f"Response was not valid JSON: {e}") from e

            if not isinstance(parsed, dict):
                raise ValueError(f"Expected a JSON object, got {type(parsed).__name__}")
            if "score" not in parsed:
                raise ValueError("JSON missing 'score' key")

            score = parsed["score"]
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise ValueError(f"Score is not a number: {score!r}")
            if isinstance(score, float) and not math.isfinite(score):
                raise ValueError(f"Score is not finite: {score!r}")
            if not (0 <= score <= 100):
                raise ValueError(f"Score out of range: {score}")

            return int(round(score))

        except ValueError as e:
            # Malformed model output: retry
            logger.warning(
                "Malformed response for candidate %s (attempt %d/%d): %s",
                candidate_id, attempt, max_attempts, e
            )

        except (groq.AuthenticationError, groq.PermissionDeniedError,
                groq.BadRequestError, groq.NotFoundError,
                groq.UnprocessableEntityError) as e:
            # Permanent errors: retrying cannot fix these
            logger.error(
                "Permanent API error for candidate %s, not retrying: %s: %s",
                candidate_id, type(e).__name__, e
            )
            return None

        except (groq.APIConnectionError, groq.APITimeoutError,
                groq.RateLimitError, groq.InternalServerError) as e:
            # Transient errors: retry
            logger.warning(
                "Transient API error for candidate %s (attempt %d/%d): %s: %s",
                candidate_id, attempt, max_attempts, type(e).__name__, e
            )

        except groq.APIStatusError as e:
            logger.error(
                "API status error %s for candidate %s: %s",
                getattr(e, "status_code", "?"), candidate_id, e
            )
            return None

        except groq.GroqError as e:
            logger.error(
                "Groq SDK error for candidate %s: %s: %s",
                candidate_id, type(e).__name__, e
            )
            return None

        except Exception:
            logger.exception("Unexpected error scoring candidate %s", candidate_id)
            return None

        # Wait before the next attempt (1s, 2s, ...)
        if attempt < max_attempts:
            time.sleep(2 ** (attempt - 1))

    logger.error("Giving up on candidate %s after %d attempts", candidate_id, max_attempts)
    return None

# Compare main user profile with all other profiles and return a sorted list of results
from database.db import read_profile, get_sheet
from src.matches import get_rejected_match
USERS_TAB = "users"

# Exclude any candidates that this user has already rejected, so we don't re-score them
def get_rejected_ids(User_ID):
    try:
        result = get_rejected_match(User_ID)
        rejected = result.get("rejected_student_id") if result.get("success") else None
    except Exception:
        logger.exception("Failed to fetch rejected matches for user %s", User_ID)
        rejected = None

    if rejected:
        # Has rejections -> exclude them (works for {id: score} dicts and lists of ids)
        return {str(r) for r in rejected}
    # New user / no rejections / lookup failed -> exclude nobody
    return set()

# Returns a list of {"user_id", "name", "score"} sorted by score (highest first). Returns [] if no candidates or an error occurred.
def AI_Profile_Matching(User_ID, groq_client):

    if User_ID is None or str(User_ID).strip() == "":
        logger.error("AI_Profile_Matching called without a User_ID")
        return []

    if groq_client is None:
        logger.error("AI_Profile_Matching called without a Groq client")
        return []

    # read_profile already handles "not found" (returns None) and
    # "duplicate ids" (raises ValueError) for us.
    try:
        main_profile = read_profile(User_ID, sheet_name=USERS_TAB)
    except ValueError as e:
        logger.error("Cannot read user %s (duplicate or invalid id): %s", User_ID, e)
        return []
    except Exception:
        logger.exception("Failed to read profile for user %s", User_ID)
        return []

    if main_profile is None:
        logger.warning("User %s not found in %s", User_ID, USERS_TAB)
        return []

    try:
        worksheet = get_sheet(USERS_TAB)
        all_profiles = worksheet.get_all_records()
    except Exception:
        logger.exception("Failed to load the '%s' sheet", USERS_TAB)
        return []

    if not isinstance(all_profiles, list):
        logger.error("Unexpected data returned from '%s' sheet", USERS_TAB)
        return []

    # Students this user has already rejected - skip them, never re-score
    rejected_ids = get_rejected_ids(User_ID)

    # Build the candidate list, skipping unusable rows
    candidates = []
    for p in all_profiles:
        if not isinstance(p, dict):
            logger.warning("Skipping non-dict row in %s: %r", USERS_TAB, p)
            continue
        cid = p.get("student_id")
        if cid is None or str(cid).strip() == "":
            logger.warning("Skipping row with missing student_id: %r", p.get("name"))
            continue
        if str(cid) == str(User_ID):
            continue
        if str(cid) in rejected_ids:
            continue
        candidates.append(p)

    if not candidates:
        logger.info("No candidates to compare against user %s", User_ID)
        return []

    results = []
    skipped = 0
    for candidate in candidates:
        try:
            score = get_compatibility_score(groq_client, main_profile, candidate)
            if score is None:
                skipped += 1
                continue
            results.append({
                "user_id": candidate["student_id"],
                "name": candidate.get("name", ""),
                "score": score
            })
        except Exception:
            # One bad candidate must never stop the run
            skipped += 1
            logger.exception(
                "Unexpected error processing candidate %s", candidate.get("student_id")
            )

    if skipped:
        logger.warning(
            "Scored %d candidates, skipped %d for user %s",
            len(results), skipped, User_ID
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    return results

# Append to recco_student_id
from database.db import add_to_recco_student_id

def Add_To_Database(User_ID, results):
    """Returns the DB outcome, or None if nothing was saved. Never raises."""

    if User_ID is None or str(User_ID).strip() == "":
        logger.error("Add_To_Database called without a User_ID")
        return None

    if not results:
        logger.info("No results to save for user %s", User_ID)
        return None

    # String keys, so they match the keys already stored in the sheet
    try:
        new_students = {str(r["user_id"]): r["score"] for r in results}
    except (KeyError, TypeError) as e:
        logger.error("Malformed results for user %s: %s", User_ID, e)
        return None

    try:
        outcome = add_to_recco_student_id(User_ID, new_students)
    except Exception:
        logger.exception("Database write failed for user %s", User_ID)
        return None

    if isinstance(outcome, dict):
        ok = outcome.get("success", False)
        error = outcome.get("error")
    else:
        ok = bool(outcome)       # guess: 0 = failure, anything else = success
        error = outcome

    if not ok:
        logger.error("Failed to add recco_student_id for %s: %s", User_ID, error)

    return outcome

def populate_recco_list(student_id: str):
    print("Populating Recco list")
    response = {"success": False, "status": 500, "reccomendations": {}}

    groq_client = None
    reccomendations = []
    try:
        groq_client = get_groq_client()
        reccomendations = AI_Profile_Matching(student_id, groq_client)
    except Exception as error:
        print("Could not generate new recommendations:", error)
    finally:
        if groq_client is not None:
            groq_client.close()

    if not reccomendations:
        print("Failed to generate new reccomendations")
        return response

    print("Reccomendations recieved!")
    add_to_db_result = Add_To_Database(student_id, reccomendations)

    # Accept either a plain 200 or a {"success": True} dict from the DB layer
    saved = add_to_db_result == 200 or (
        isinstance(add_to_db_result, dict) and add_to_db_result.get("success")
    )
    if not saved:
        print("Failed to save new reccomendations")
        return response

    response["status"] = 200
    response["success"] = True
    response["reccomendations"] = reccomendations
    return response


# TESTING
if __name__ == "__main__":
    USER_ID = 2403007  # <-- set the main user to match

    groq_client = get_groq_client()
    results = AI_Profile_Matching(USER_ID, groq_client)
    Add_To_Database(USER_ID, results)

    # For inspection only - not written to the sheet
    name_score = {r["name"]: r["score"] for r in results}
    print(name_score)