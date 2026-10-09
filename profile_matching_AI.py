"""
AI Profile Matching
--------------------
Reads user profiles from a Google Sheet, scores compatibility between a
given main user and every other user via the Groq API, and writes the
results back to a "Matches" tab in the same spreadsheet.
 
Setup required:
1. pip install gspread google-auth groq
2. A Google Cloud service account JSON key (credentials.json), shared
   with edit access to your spreadsheet.
3. Environment variable PROFILE_MATCHING_API_KEY set to your Groq API key.
4. A "Profiles" tab with at least columns: User_ID, Name, Interests, ... etc.
5. A "Matches" tab with header row: Main_User_ID, Matched_User_ID, Matched_Name, Score
"""

# Profile Database: https://docs.google.com/spreadsheets/d/1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU/edit?usp=sharing

import os
import json
import gspread
from google.oauth2.service_account import Credentials
from groq import Groq

# Set Up Spreadsheet
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU/edit?usp=sharing"
PROFILES_TAB = "users"
MATCHES_TAB = "matches"
 
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

FIELDS_FOR_AI = [
    "birthday", "gender", "course", "bio", "religion", "mbti",
    "match_preference", "here_for", "expectations", "ccas",
    "events", "hobbies", "interest_groups"
]

def filter_profile_fields(profile):
    """Keep only the allowlisted fields before sending a profile to the AI."""
    return {field: profile.get(field, "") for field in FIELDS_FOR_AI}

def get_sheets_client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)
 
def get_groq_client():
    return Groq(api_key=os.getenv("PROFILE_MATCHING_API_KEY"))

def get_spreadsheet(gc):
    return gc.open_by_url(SPREADSHEET_URL)

# ---------------------------------------------------------------------
# Step 1: Retrieve profiles
# ---------------------------------------------------------------------
 
def Retrieve_Profiles(User_ID, all_profiles):
    """Split all profiles into (main_profile, candidate_profiles)."""
    main_profile = None
    candidate_profiles = []
 
    for profile in all_profiles:
        if str(profile["student_id"]) == str(User_ID):
            main_profile = profile
        else:
            candidate_profiles.append(profile)
 
    return main_profile, candidate_profiles

# ---------------------------------------------------------------------
# Step 2: Score a single pair of profiles via the Groq API
# ---------------------------------------------------------------------
 
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
            model="llama-3.3-70b-versatile",
            max_tokens=50,
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

 # ---------------------------------------------------------------------
# Step 3: Main workflow - score the main user against every candidate
# ---------------------------------------------------------------------
 
def AI_Profile_Matching(User_ID, gc, groq_client):
    spreadsheet = get_spreadsheet(gc)
    sheet = spreadsheet.worksheet(PROFILES_TAB)
    all_profiles = sheet.get_all_records()
 
    main_profile, candidates = Retrieve_Profiles(User_ID, all_profiles)
 
    if main_profile is None:
        print(f"User {User_ID} not found in {PROFILES_TAB}")
        return []
 
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

# ---------------------------------------------------------------------
# Step 4: Write results back to the Matches tab (full replace per user)
# ---------------------------------------------------------------------
 
def Add_To_Database(User_ID, results, gc):
    spreadsheet = get_spreadsheet(gc)
    matches_sheet = spreadsheet.worksheet(MATCHES_TAB)
    all_rows = matches_sheet.get_all_records()
    headers = matches_sheet.row_values(1)
 
    recco_col_index = headers.index("recco_student_id") + 1  # 1-based for gspread
 
    new_reccos = [{"id": r["user_id"], "score": r["score"]} for r in results]
 
    # Find the row for this student_id (data starts at row 2)
    row_number = None
    existing_recco_raw = ""
    for i, row in enumerate(all_rows, start=2):
        if str(row["student_id"]) == str(User_ID):
            row_number = i
            existing_recco_raw = str(row.get("recco_student_id", "") or "")
            break
 
    # Parse existing JSON, falling back to an empty list if blank/invalid
    try:
        existing_reccos = json.loads(existing_recco_raw) if existing_recco_raw else []
        if not isinstance(existing_reccos, list):
            existing_reccos = []
    except json.JSONDecodeError:
        print(f"Warning: could not parse existing recco_student_id for student {User_ID}, overwriting")
        existing_reccos = []
 
    existing_ids = {entry.get("id") for entry in existing_reccos}
 
    # Append only new ids, avoid duplicates, keep existing scores as-is
    combined_reccos = existing_reccos + [r for r in new_reccos if r["id"] not in existing_ids]
    combined_value = json.dumps(combined_reccos)
 
    if row_number is not None:
        # Row exists - update only the recco_student_id cell
        matches_sheet.update_cell(row_number, recco_col_index, combined_value)
    else:
        # No row yet for this student - create one, leaving accepted/rejected blank
        new_row = [""] * len(headers)
        new_row[headers.index("student_id")] = User_ID
        new_row[recco_col_index - 1] = combined_value
        matches_sheet.append_row(new_row)

# ---------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------
 
if __name__ == "__main__":
    USER_ID = 1001  # <-- set the main user to match
 
    gc = get_sheets_client()
    groq_client = get_groq_client()
 
    results = AI_Profile_Matching(USER_ID, gc, groq_client)
    Add_To_Database(USER_ID, results, gc)
 
    # For inspection only - not written to the sheet
    name_score = {r["name"]: r["score"] for r in results}
    print(name_score)