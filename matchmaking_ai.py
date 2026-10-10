import os
import json
import time
import asyncio
import logging

import groq
from groq import Groq
from dotenv import load_dotenv

# Team code. This file sits in the repo root (if you move it into src/, use `from matches import ...`).
from src.matches import get_accepted_match
from database.db import get_profile

logger = logging.getLogger(__name__)
load_dotenv()   # reads MATCHMAKING_API_KEY from .env


# ======================================================================
# CONFIG
# ======================================================================

GROQ_MODEL = "openai/gpt-oss-120b"
MAX_ATTEMPTS = 3                     # tries per call before giving up
RETRY_WAIT_SECONDS = 2               # wait before retry #2; doubles each time (2s, 4s...)
API_TIMEOUT_SECONDS = 30             # give up on a single API call after this long
MAX_ITEMS_PER_LIST = 5               # keep messages short enough for Telegram

# Profile fields sent to the AI 
PROFILE_FIELDS = [
    "birthday", "gender", "year", "course", "bio", "religion",
    "mbti", "match_preference", "here_for", "expectations", "ccas",
    "events", "hobbies", "interest_groups",
]

# The 3 lists we expect back from the AI.
OUTPUT_KEYS = ("common_interests", "conversation_starters", "outing_ideas")

# What the bot gets back about each person (to show who the match is).
CONTACT_FIELDS = ("student_id", "name", "insta_handle", "telegram_handle")


# ======================================================================
# PART 1: AI MODULE (API interaction)
# ======================================================================

def _profile_to_text(profile: dict) -> str:
    """One profile -> lines like 'hobbies: reading, baking' (empty fields skipped)."""
    lines = []
    for field in PROFILE_FIELDS:
        value = profile.get(field)
        if value in (None, "", [], ()):
            continue
        if isinstance(value, (list, tuple)):
            value = ", ".join(str(v) for v in value)
        lines.append(f"{field}: {value}")
    return "\n".join(lines)


def build_prompt(profile_a: dict, profile_b: dict) -> str:
    """STEP 1: turn the two profiles (the input record) into the prompt text."""
    return f"""You are helping two university students who just matched on
an app for their school. Compare their profiles and help them start
talking.

Student A:
{_profile_to_text(profile_a)}

Student B:
{_profile_to_text(profile_b)}

Reply with ONLY valid JSON (no markdown fences, no extra text), in exactly
this shape:
{{
  "common_interests": ["...", "..."],
  "conversation_starters": ["...", "...", "..."],
  "outing_ideas": ["...", "...", "..."]
}}

Give 3-{MAX_ITEMS_PER_LIST} short, one-sentence items per list. Only use what's actually in
the two profiles, don't invent facts about them.

common_interests must NEVER be empty. List real overlaps first (same hobby,
CCA, course, or what they are looking for). If there are none, list the
closest real connections instead: related or complementary interests (e.g.
sketching and robotics are both creative, hands-on hobbies) or similar goals.
Do not use trivial filler like "both are students".

Do NOT use anyone's name, or "Student A" / "Student B", anywhere. Write each
conversation starter as something one student could say directly to the
other (e.g. "What's your favourite hiking trail?")."""


_client = None


def _get_client() -> Groq:
    """Creates the Groq client once. Raises if MATCHMAKING_API_KEY is missing."""
    global _client
    if _client is None:
        # max_retries=0: we do our own retrying below, so waits don't stack up.
        _client = Groq(api_key=os.getenv("MATCHMAKING_API_KEY"),
                       timeout=API_TIMEOUT_SECONDS, max_retries=0)
    return _client


def call_api(client: Groq, prompt: str) -> str:
    """STEP 2: send the prompt, return the AI's raw text."""
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content or ""


def parse_response(raw_text: str) -> dict:
    """STEP 3: pull the JSON out of the reply (ignores ```json fences / extra words).
    Raises ValueError if it isn't valid JSON."""
    start, end = raw_text.find("{"), raw_text.rfind("}")
    return json.loads(raw_text[start:end + 1])


def validate_response(data: dict) -> dict:
    """STEP 4: check the schema. Each of the 3 keys must be a non-empty list of
    text. Returns a clean dict with only those keys, or raises ValueError."""
    clean = {}
    for key in OUTPUT_KEYS:
        items = data.get(key)
        if not isinstance(items, list) or not all(isinstance(i, str) for i in items):
            raise ValueError(f"'{key}' is missing or not a list of text")
        items = [i.strip() for i in items if i.strip()]
        if not items:
            raise ValueError(f"'{key}' is empty")
        clean[key] = items[:MAX_ITEMS_PER_LIST]   # cap the length
    return clean


# Problems worth retrying: bad output (ValueError), network trouble, rate limit,
# server error. Anything else (wrong API key, retired model...) won't fix itself.
_RETRYABLE = (ValueError, groq.APIConnectionError,
              groq.RateLimitError, groq.InternalServerError)


def generate_suggestions(profile_a: dict, profile_b: dict) -> dict:
    """
    THE AI MODULE'S MAIN FUNCTION. Never raises.
      success -> {"success": True, "common_interests": [...], "conversation_starters": [...], "outing_ideas": [...]}
      failure -> {"success": False, "error": "..."}   (also logged)
    """
    try:
        prompt = build_prompt(profile_a, profile_b)
        client = _get_client()
    except Exception as e:
        logger.error("matchmaking_ai: setup failed: %s: %s", type(e).__name__, e)
        return {"success": False, "error": f"{type(e).__name__}: {e}"}

    last_error = "unknown error"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            raw_text = call_api(client, prompt)
            return {"success": True, **validate_response(parse_response(raw_text))}
        except _RETRYABLE as e:                       # worth another try
            last_error = f"{type(e).__name__}: {e}"
            logger.warning("matchmaking_ai: attempt %d/%d failed: %s",
                           attempt, MAX_ATTEMPTS, last_error)
        except Exception as e:                        # won't fix itself - stop now
            logger.error("matchmaking_ai: API call failed: %s: %s", type(e).__name__, e)
            return {"success": False, "error": f"{type(e).__name__}: {e}"}

        if attempt < MAX_ATTEMPTS:
            time.sleep(RETRY_WAIT_SECONDS * 2 ** (attempt - 1))   # wait longer each time

    logger.error("matchmaking_ai: giving up after %d attempts: %s", MAX_ATTEMPTS, last_error)
    return {"success": False, "error": last_error}


async def generate_suggestions_async(profile_a: dict, profile_b: dict) -> dict:
    """Same as generate_suggestions, but won't freeze an async bot while waiting."""
    return await asyncio.to_thread(generate_suggestions, profile_a, profile_b)


# ======================================================================
# PART 2: INPUT ADAPTER (reads src/matches.py, feeds PART 1)
# ======================================================================

def _load_profile(student_id: str) -> dict | None:
    """One student's profile dict, or None if it can't be loaded."""
    try:
        profile = get_profile(student_id)
    except Exception as e:
        logger.error("matchmaking_ai: couldn't load profile %s: %s: %s",
                     student_id, type(e).__name__, e)
        return None
    return profile if isinstance(profile, dict) and profile.get("student_id") else None


def _split_ids(value) -> list[str]:
    """['1013, 1002, 1009'] -> ['1013', '1002', '1009']
    (the database packs several IDs into one piece of text)."""
    if not isinstance(value, (list, tuple)):      # a single value instead of a list
        value = [value or ""]
    return [i.strip() for item in value for i in str(item).split(",") if i.strip()]


def _accepted_ids(student_id: str) -> list[str]:
    """IDs this student accepted. matches.py returns {'success': True, 'accepted_student_id': [...]}."""
    result = get_accepted_match(student_id)
    if not result.get("success"):
        logger.error("matchmaking_ai: couldn't read accepted list for %s: %s",
                     student_id, result.get("error"))
        return []
    return _split_ids(result.get("accepted_student_id"))


def _mutual_match_ids(user_id: str) -> list[str]:
    """Students who accepted user_id AND whom user_id accepted."""
    return [other for other in _accepted_ids(user_id)
            if other != user_id and user_id in _accepted_ids(other)]


def get_matches_for_user(user_id: str) -> list[dict]:
    """MAIN ENTRY POINT: one result dict per mutual match of user_id
    (user_a = the person asking, user_b = their match). [] = no matches yet.
    Success -> user_a_info, user_b_info + the 3 lists. Failure -> success False + error."""
    user_id = str(user_id).strip()
    match_ids = _mutual_match_ids(user_id)                       # e.g. ['1013', '1002', '1009']
    profile_a = _load_profile(user_id) if match_ids else None    # loaded once, reused below

    results = []
    for other_id in match_ids:
        result = {"user_a": user_id, "user_b": other_id}
        profile_b = _load_profile(other_id)
        if profile_a is None or profile_b is None:
            missing = user_id if profile_a is None else other_id
            result.update(success=False, error=f"no profile found for {missing}")
        else:
            result["user_a_info"] = {f: profile_a.get(f) for f in CONTACT_FIELDS}
            result["user_b_info"] = {f: profile_b.get(f) for f in CONTACT_FIELDS}
            result.update(generate_suggestions(profile_a, profile_b))
        results.append(result)
    return results


async def get_matches_for_user_async(user_id: str) -> list[dict]:
    """Same as get_matches_for_user, but won't freeze an async bot while waiting."""
    return await asyncio.to_thread(get_matches_for_user, user_id)


def format_recommendations(result: dict, for_user: str = "a") -> str:
    """One result dict -> plain-text message to send. for_user="a" writes it for
    user_a about user_b; "b" is the other way round."""
    if not result.get("success"):
        return "Sorry, we couldn't generate suggestions for this match right now."

    other = result["user_b_info"] if for_user == "a" else result["user_a_info"]
    lines = [f"You matched with {other.get('name') or 'someone new'}!"]
    if other.get("telegram_handle"):
        lines.append(f"Telegram: {other['telegram_handle']}")
    if other.get("insta_handle"):
        lines.append(f"Instagram: {other['insta_handle']}")

    for title, key in [("Things you have in common", "common_interests"),
                       ("Conversation starters", "conversation_starters"),
                       ("Outing ideas", "outing_ideas")]:
        lines += ["", f"{title}:"] + [f"- {item}" for item in result[key]]
    return "\n".join(lines)

# ---------- TEMPORARY TEST  ----------
if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)   # show any problems in the terminal
    TEST_STUDENT_ID = "1002"                     # <-- change to a real student ID

    results = get_matches_for_user(TEST_STUDENT_ID)
    print(f"\n{TEST_STUDENT_ID} has {len(results)} mutual match(es)\n")
    for r in results:
        if r["success"]:
            print(format_recommendations(r))
        else:
            print(f"FAILED for {r['user_b']}: {r['error']}")
        print("-" * 40)
# -------------------------------------------------------------------------------------