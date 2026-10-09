import os
import csv
import json
import io
import time

import requests
import groq
from groq import Groq
from dotenv import load_dotenv


_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(dotenv_path=_env_path)


# ======================================================================
# SECTION 1: CONFIG
# ======================================================================

PROFILES_TAB_GID = "0"                         
MATCHES_TAB_GID = "577783517"  

COL_SWIPER_ID = "student_id"
COL_SWIPED_ID = "accepted_student_id"

# --- Column names inside the "users" tab -----------------------------------
PROFILE_ID_COLUMN = "student_id"
PROFILE_FIELDS = [   # these are the fields sent to the AI
    "name", "birthday", "gender", "year", "course", "bio", "religion",
    "mbti", "match_preference", "here_for", "expectations", "ccas",
    "events", "hobbies", "interest_groups",
]
# insta_handle / tele_handle are NOT sent to the AI (not compatibility info),
# but they ARE returned in user_a_info / user_b_info for the front-end.

# --- Groq model name ---------------------------------------------------------
# CHANGE THIS if Groq retires it (see console.groq.com/docs/deprecations).
GROQ_MODEL = "openai/gpt-oss-120b"

# How long (seconds) to reuse a downloaded sheet before fetching it again.
CACHE_SECONDS = 30


# ======================================================================
# SECTION 2: GOOGLE SHEETS
# ======================================================================

_csv_cache: dict[str, tuple[float, list[dict]]] = {}  # gid -> (time fetched, rows)


def _fetch_tab_as_dicts(gid: str) -> list[dict]:
    """Downloads one sheet tab as CSV -> list of dicts keyed by header row."""
    cached = _csv_cache.get(gid)
    if cached and time.time() - cached[0] < CACHE_SECONDS:
        return cached[1]

    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"

    response = requests.get(url, timeout=15)
    response.raise_for_status()  # errors if the sheet isn't shared / gid is wrong

    rows = list(csv.DictReader(io.StringIO(response.text)))
    _csv_cache[gid] = (time.time(), rows)
    return rows


def get_all_swipes() -> list[dict]:
    """Returns every row of the matches tab as a list of dicts."""
    if not str(MATCHES_TAB_GID).isdigit():
        raise ValueError("Set MATCHES_TAB_GID at the top of matchmaking_ai.py "
                         "to the matches tab's gid (the number after #gid= in the URL).")
    return _fetch_tab_as_dicts(MATCHES_TAB_GID)


def get_profile(user_id: str) -> dict | None:
    """Looks up one user's profile row by student ID. None if not found."""
    user_id = str(user_id).strip()
    for row in _fetch_tab_as_dicts(PROFILES_TAB_GID):
        if str(row.get(PROFILE_ID_COLUMN, "")).strip() == user_id:
            return row
    return None


# ======================================================================
# SECTION 3: MATCHING LOGIC — did both users accept each other?
# ======================================================================

def _split_ids(cell) -> list[str]:
    """Turns one sheet cell like '1008, 1007' into ['1008', '1007'].
    A blank cell gives an empty list."""
    if not cell:
        return []
    return [part.strip() for part in str(cell).split(",") if part.strip()]


def get_mutual_matches(swipe_records: list[dict] | None = None) -> list[tuple[str, str]]:
    """
    Returns only the pairs where BOTH people accepted each other,
    e.g. [("1001", "1008")]. Each pair appears once.

    swipe_records: optional list of row dicts for testing without the sheet.
    """
    if swipe_records is None:
        swipe_records = get_all_swipes()

    # Step 1: every "A accepted B" as a directed pair. Each row is one
    # student, and their accepted cell can list several IDs.
    liked_pairs = set()
    for row in swipe_records:
        swiper = str(row[COL_SWIPER_ID]).strip()
        if not swiper:
            continue
        for swiped in _split_ids(row[COL_SWIPED_ID]):
            if swiped != swiper:  # ignore a student "accepting" themselves
                liked_pairs.add((swiper, swiped))

    # Step 2: mutual = (A, B) exists AND (B, A) exists
    matches = []
    already_added = set()
    for (a, b) in liked_pairs:
        if (b, a) in liked_pairs:
            pair = tuple(sorted((a, b)))  # so (A,B) and (B,A) count once
            if pair not in already_added:
                already_added.add(pair)
                matches.append(pair)
    return matches


# ======================================================================
# SECTION 4: AI CONVERSATION SUGGESTIONS (Groq)
# ======================================================================

_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        _groq_client = Groq(api_key=os.getenv("MATCHMAKING_API_KEY"))
    return _groq_client


def _profile_to_text(profile: dict) -> str:
    """Turns a profile dict into a readable text block for the AI prompt."""
    lines = []
    for field in PROFILE_FIELDS:
        value = profile.get(field)
        if value not in (None, ""):
            lines.append(f"{field}: {value}")
    return "\n".join(lines)


def _contact_info(profile: dict) -> dict:
    """The details the front-end needs to show who the match is."""
    return {
        "student_id": profile.get(PROFILE_ID_COLUMN),
        "name": profile.get("name"),
        "insta_handle": profile.get("insta_handle"),
        "tele_handle": profile.get("telegram_handle"),
    }


def _generate_content_with_retry(client, prompt: str, max_attempts: int = 4):
    """Calls Groq; retries with a growing wait if the server is busy (5xx)."""
    wait_seconds = 2
    for attempt in range(1, max_attempts + 1):
        try:
            return client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
        except groq.InternalServerError:
            if attempt == max_attempts:
                raise
            print(f"Groq is busy (attempt {attempt}/{max_attempts}), "
                  f"retrying in {wait_seconds}s...")
            time.sleep(wait_seconds)
            wait_seconds *= 2  # 2s, 4s, 8s...


def AI_Conversation(user_a_id: str, user_b_id: str) -> dict:
    """
    Takes two matched student IDs, reads both profiles, asks the AI for
    conversation starters / common interests / date ideas, and RETURNS the
    result dict described at the top of this file.
    Raises ValueError if either student has no profile.
    """
    profile_a = get_profile(user_a_id)
    profile_b = get_profile(user_b_id)

    if profile_a is None or profile_b is None:
        missing_id = user_a_id if profile_a is None else user_b_id
        raise ValueError(f"No profile found for user_id={missing_id}")

    prompt = f"""You are helping two university students who just matched on
a dating app for their school. Based on their profiles below, suggest
things that could help them start talking.

Student A:
{_profile_to_text(profile_a)}

Student B:
{_profile_to_text(profile_b)}

Reply with ONLY valid JSON (no markdown fences, no extra text), in exactly
this shape:
{{
  "conversation_starters": ["...", "...", "..."],
  "common_interests": ["...", "..."],
  "date_ideas": ["...", "...", "..."]
}}

Give 3-5 short, one-sentence items per list. Only use what's actually in
the two profiles — don't invent shared interests that aren't there."""

    client = _get_groq_client()
    response = _generate_content_with_retry(client, prompt)
    raw_text = response.choices[0].message.content.strip()

    # The AI was told to return pure JSON, but strip code fences just in case
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        if raw_text.startswith("json"):
            raw_text = raw_text[4:].strip()

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # One bad AI reply shouldn't crash the bot
        parsed = {
            "conversation_starters": [],
            "common_interests": [],
            "date_ideas": [],
            "raw_response": raw_text,
        }

    return {
        "user_a": user_a_id,
        "user_b": user_b_id,
        "user_a_info": _contact_info(profile_a),
        "user_b_info": _contact_info(profile_b),
        **parsed,
    }


# ======================================================================
# SECTION 5: FUNCTIONS FOR TEAMMATES (Raphael take info form here)
# ======================================================================

def _safe_ai_conversation(user_a_id: str, user_b_id: str) -> dict:
    """Like AI_Conversation, but a failure for one pair returns an
    {"error": ...} dict instead of crashing the whole list."""
    try:
        return AI_Conversation(user_a_id, user_b_id)
    except Exception as e:
        return {"user_a": user_a_id, "user_b": user_b_id, "error": str(e)}


def get_all_match_suggestions() -> list[dict]:
    """RETURNS a result dict for every mutual match in the sheet.
    (One AI call per match, so many matches = slower.)"""
    return [_safe_ai_conversation(a, b) for a, b in get_mutual_matches()]


def get_matches_for_user(user_id: str) -> list[dict]:
    """RETURNS a result dict for each mutual match that involves user_id.
    In each dict, user_a is always the person asking (user_id) and user_b
    is their match."""
    user_id = str(user_id).strip()
    results = []
    for a, b in get_mutual_matches():
        if user_id == a:
            other = b
        elif user_id == b:
            other = a
        else:
            continue  # this pair doesn't involve our user
        results.append(_safe_ai_conversation(user_id, other))
    return results


# ======================================================================
# SECTION 6: SELF-TEST (only runs with `python matchmaking_ai.py`,
# never when a teammate imports this file)
# ======================================================================
if __name__ == "__main__":
    results = get_all_match_suggestions()
    print(f"Found {len(results)} mutual match(es)\n")
    print(json.dumps(results, indent=2, ensure_ascii=False))