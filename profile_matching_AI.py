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
SPREADSHEET_NAME = "https://docs.google.com/spreadsheets/d/1N_2QPdtVigDzzmyjlyUB_AIdLArnxbScmLbq0s2UCdU/edit?usp=sharing"
PROFILES_TAB = "users"
MATCHES_TAB = "matches"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheets_client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)
 
def get_groq_client():
    return Groq(api_key=os.getenv("PROFILE_MATCHING_API_KEY"))

# ---------------------------------------------------------------------
# Step 1: Retrieve profiles
# ---------------------------------------------------------------------
 
def Retrieve_Profiles(User_ID, all_profiles):
    """Split all profiles into (main_profile, candidate_profiles)."""
    main_profile = None
    candidate_profiles = []
 
    for profile in all_profiles:
        if profile["User_ID"] == User_ID:
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
        "profile_a": main_profile,
        "profile_b": candidate_profile
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
        print(f"Validation failed for candidate {candidate_profile.get('User_ID')}: {e}")
        return None
    except Exception as e:
        print(f"API call failed for candidate {candidate_profile.get('User_ID')}: {e}")
        return None
 
 # ---------------------------------------------------------------------
# Step 3: Main workflow - score the main user against every candidate
# ---------------------------------------------------------------------
 
def AI_Profile_Matching(User_ID, gc, groq_client):
    sheet = gc.open(SPREADSHEET_NAME).worksheet(PROFILES_TAB)
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
                "user_id": candidate["User_ID"],
                "name": candidate["Name"],
                "score": score
            })
 
    results.sort(key=lambda r: r["score"], reverse=True)
    return results

# ---------------------------------------------------------------------
# Step 4: Write results back to the Matches tab (full replace per user)
# ---------------------------------------------------------------------
 
def Add_To_Database(User_ID, results, gc):
    results_sheet = gc.open(SPREADSHEET_NAME).worksheet(MATCHES_TAB)
    existing = results_sheet.get_all_records()
 
    # Keep rows belonging to other users, drop this user's old rows
    rows_to_keep = [row for row in existing if row["Main_User_ID"] != User_ID]
 
    new_rows = [
        {
            "Main_User_ID": User_ID,
            "Matched_User_ID": r["user_id"],
            "Matched_Name": r["name"],
            "Score": r["score"]
        }
        for r in results
    ]
 
    all_rows = rows_to_keep + new_rows
 
    results_sheet.clear()
    results_sheet.append_row(["Main_User_ID", "Matched_User_ID", "Matched_Name", "Score"])
    for row in all_rows:
        results_sheet.append_row([
            row["Main_User_ID"],
            row["Matched_User_ID"],
            row["Matched_Name"],
            row["Score"]
        ])
 