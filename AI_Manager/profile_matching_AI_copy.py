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

from models.user import User

# Only fields that exist on User. No name, student_id, or handles:
# the AI doesn't need identifying info to score compatibility.
FIELDS_FOR_AI = [
    "age", "gender", "course", "bio", "religion", "mbti",
    "match_preference", "here_for", "expectations",
    "ccas", "events", "hobbies", "interest_groups",
]

LIST_FIELDS = ("ccas", "events", "hobbies", "interest_groups")

def to_user(profile) -> User:
    """Accepts a User or a raw sheet row (dict) and returns a User."""
    if isinstance(profile, User):
        return profile
    if not isinstance(profile, dict):
        raise ValueError(f"Profile must be a User or dict, got {type(profile).__name__}")

    data = profile.copy()
    # Sheets usually store lists as "a, b, c" strings (or "" when empty)
    for key in LIST_FIELDS:
        value = data.get(key)
        if isinstance(value, str):
            data[key] = [v.strip() for v in value.split(",") if v.strip()]
    return User.from_dict(data)


def user_to_ai_dict(user: User) -> dict:
    """The subset of a User that gets sent to the AI. None becomes ''."""
    details = user.get_user_details()
    return {f: details.get(f) if details.get(f) is not None else "" for f in FIELDS_FOR_AI}

# Call GROQ AI to get a compatibility score for a pair of profiles
def get_compatibility_score(client, main_user: User, candidate: User):
    """Scores ONE pair of Users. Returns an int 0-100, or None on failure. Never raises."""

    max_attempts = 3

    if client is None:
        logger.error("No Groq client supplied")
        return None

    try:
        main_user = to_user(main_user)
        candidate = to_user(candidate)
    except (ValueError, TypeError) as e:
        logger.warning("Skipping: bad profile data: %s", e)
        return None

    candidate_id = candidate.student_id

    instructions = (
    "You compare two user dating/matching profiles and return a single "
    "compatibility score from 0 to 100, based on shared interests, "
    "lifestyle, and stated preferences. "
    "Respond ONLY with valid JSON in this exact format, no other text: "
    '{"score": <integer 0-100>}'
    )

    try:
        payload = {
            "profile_a": user_to_ai_dict(main_user),
            "profile_b": user_to_ai_dict(candidate),
        }
        user_content = json.dumps(payload, default=str)
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

if __name__ == "__main__":
    a = User(student_id="1", name="Alex", age=21, gender="M", course="CS",
             mbti="INTJ", hobbies=["climbing", "chess"], here_for="Something long-term")
    b = User(student_id="2", name="Sam", age=22, gender="F", course="Data Science",
             mbti="ENFP", hobbies=["climbing", "baking"], here_for="Something long-term")
    c = User(student_id="3", name="Jo", age=40, gender="F", course="Law",
         mbti="ESTP", hobbies=["clubbing"], here_for="Something casual")

    client = get_groq_client()
    print("A vs B:", get_compatibility_score(client, a, b))
    print("A vs C:", get_compatibility_score(client, a, c))
    client.close()