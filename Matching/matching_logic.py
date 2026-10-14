import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src import matches 
from src.matches import add_accepted_match, add_rejected_match, get_accepted_match, get_rejected_match
from database import db
import profile_matching_AI

VALID_DECISIONS = ("accept", "reject")
current_match = 0

def load_matches(id):
    recco_ids = db.get_user_recco_student_id(id)

    if not isinstance(recco_ids, dict) or not recco_ids.get("success"):
        return None

    recommended = recco_ids.get("recco_student_id", {})

    accepted_result = get_accepted_match(id)
    rejected_result = get_rejected_match(id)

    accepted_ids = set()
    rejected_ids = set()

    if isinstance(accepted_result, dict) and accepted_result.get("success"):
        accepted_ids = set(accepted_result.get("accepted_student_id", []))

    if isinstance(rejected_result, dict) and rejected_result.get("success"):
        rejected_ids = set(rejected_result.get("rejected_student_id", []))

    excluded_ids = accepted_ids | rejected_ids

    filtered_matches = {
        student_id: score
        for student_id, score in recommended.items()
        if student_id not in excluded_ids
    }

    return filtered_matches


def compatibility_label(score):
    """Convert a compatibility score into the team's score band."""
    try:
        score = int(score)
    except (TypeError, ValueError):
        return None

    if not 0 <= score <= 100:
        return None

    if score >= 85:
        return "High Compatibility ✨"
    if score >= 70:
        return "Moderate Compatibility 🔥"
    return "Low Compatibility 🤔"

def show_next_match(recommendations):
    global current_match

    item = get_next_match(recommendations, current_match)

    if item is None:
        return False

    student_id, score = item
    current_match += 1

    profile = db.get_profile(student_id)
    return profile, score

def check_user_decision(decision):
    return decision.lower() in VALID_DECISIONS

def get_accepted_students(student_id):
    """Read one student's accepted list through matches.py."""
    result = matches.get_accepted_match(str(student_id))

    if not isinstance(result, dict) or not result.get("success"):
        return {
            "success": False,
            "accepted_student_id": [],
            "error": (
                result.get("error", "Unable to get accepted matches")
                if isinstance(result, dict)
                else "Unable to get accepted matches"
            ),
        }

    accepted = result.get("accepted_student_id")

    return {
        "success": True,
        "accepted_student_id": accepted,
    }
def _clean_ids(value):
    """Turn a stored accepted list into clean ID strings.
    Handles ['1013', '1002'] and also packed cells like ['1013, 1002, 1009']."""
    if not isinstance(value, (list, tuple)):
        value = [value or ""]
    return [i.strip() for item in value for i in str(item).split(",") if i.strip()]


def is_mutual_match(student_id, target_id, accepted_ids=None):
    student_id = str(student_id)
    target_id = str(target_id)

    # Read your accepted list only if the caller hasn't supplied it.
    if accepted_ids is None:
        first = get_accepted_students(student_id)

        if not first["success"]:
            raise RuntimeError(
                "Could not read your accepted matches. Please try again later."
            )

        accepted_ids = _clean_ids(first["accepted_student_id"])

    if target_id not in accepted_ids:
        return False

    second = get_accepted_students(target_id)

    if not second["success"]:
        raise RuntimeError(
            f"Could not check student {target_id}: "
            f"{second.get('error', 'Unknown error')}"
        )

    return student_id in _clean_ids(second["accepted_student_id"])

def handle_match_decision(student_id, target_id, decision):
    """Main function for the rest of the project to call.

    Returns one of:
        rejected -> user rejected the recommended student
        waiting  -> user accepted, but it is not mutual yet
        matched  -> both users accepted; contact can be released
        error    -> decision could not be saved
    """
    choice = create_match_decision(
        student_id,
        target_id,
        decision,
    )

    if choice is None:
        return {
            "success": False,
            "status": "error",
            "matched": False,
            "release_contact": False,
            "error": "Decision must be accept or reject",
        }

    if choice["decision"] == "reject":
        result = record_reject(
            choice["student_id"],
            choice["target_id"],
        )

        if not result["success"]:
            return {
                "success": False,
                "status": "error",
                "matched": False,
                "release_contact": False,
                "error": result.get("error"),
            }

        return {
            "success": True,
            "status": "rejected",
            "matched": False,
            "release_contact": False,
        }

    result = record_accept(
        choice["student_id"],
        choice["target_id"],
    )

    if not result["success"]:
        return {
            "success": False,
            "status": "error",
            "matched": False,
            "release_contact": False,
            "error": result.get("error"),
        }

    if is_mutual_match(
        choice["student_id"],
        choice["target_id"],
    ):
        return {
            "success": True,
            "status": "matched",
            "matched": True,
            "release_contact": True,
        }

    return {
        "success": True,
        "status": "waiting",
        "matched": False,
        "release_contact": False,
    }

def create_match_decision(student_id, target_id, decision):
    """Validate an Accept/Reject choice before anything is written."""
    student_id = str(student_id).strip()
    target_id = str(target_id).strip()
    decision = str(decision).strip().lower()

    if not student_id or not target_id:
        return None

    if student_id == target_id:
        return None

    if decision not in VALID_DECISIONS:
        return None

    return {
        "student_id": student_id,
        "target_id": target_id,
        "decision": decision,
    }

def record_accept(student_id, target_id): 
    """Save an Accept using the existing matches.py database functions."""
    decision = create_match_decision(
        student_id,
        target_id,
        "accept",
    )

    if decision is None:
        return {
            "success": False,
            "error": "Invalid accept decision",
        }

    # Do not add the same student twice if the database already has it.
    current = get_accepted_students(decision["student_id"])

    if not current["success"]:
        return current

    if decision["target_id"] not in current["accepted_student_id"]:
        result = matches.add_accepted_match(
            decision["student_id"],
            [decision["target_id"]],
        )

        if not isinstance(result, dict) or not result.get("success"):
            return {
                "success": False,
                "error": (
                    result.get("error", "Unable to save accept")
                    if isinstance(result, dict)
                    else "Unable to save accept"
                ),
            }

    # Once the user has decided, remove that student from recommendations.
    removed = matches.remove_recco_student_id(
        decision["student_id"],
        [decision["target_id"]],
    )

    return {
        "success": True,
        "decision": "accept",
        "student_id": decision["student_id"],
        "target_id": decision["target_id"],
        "recommendation_removed": bool(
            isinstance(removed, dict) and removed.get("success")
        ),
    }

def record_reject(student_id, target_id):
    """Save a Reject using the existing matches.py database functions."""
    decision = create_match_decision(
        student_id,
        target_id,
        "reject",
    )

    if decision is None:
        return {
            "success": False,
            "error": "Invalid reject decision",
        }

    # If this user had accepted before, Reject should override that choice.
    current = get_accepted_students(decision["student_id"])

    if current["success"] and (
        decision["target_id"] in current["accepted_student_id"]
    ):
        removed_accept = matches.remove_accepted_match(
            decision["student_id"],
            [decision["target_id"]],
        )

        if (
            not isinstance(removed_accept, dict)
            or not removed_accept.get("success")
        ):
            return {
                "success": False,
                "error": "Unable to remove previous accepted match",
            }

    result = matches.add_rejected_match(
        decision["student_id"],
        [decision["target_id"]],
    )

    if not isinstance(result, dict) or not result.get("success"):
        return {
            "success": False,
            "error": (
                result.get("error", "Unable to save reject")
                if isinstance(result, dict)
                else "Unable to save reject"
            ),
        }

    removed = matches.remove_recco_student_id(
        decision["student_id"],
        [decision["target_id"]],
    )

    return {
        "success": True,
        "decision": "reject",
        "student_id": decision["student_id"],
        "target_id": decision["target_id"],
        "recommendation_removed": bool(
            isinstance(removed, dict) and removed.get("success")
        ),

    }

def sort_matches_by_score(match_dict):
    # Convert spreadsheet text into a Python dictionary.
    if isinstance(match_dict, str):
        match_dict = json.loads(match_dict or "{}")

    return sorted(
        match_dict.items(),
        key=lambda item: int(item[1]),
        reverse=True,
    )

def get_next_user(student_id: str):
    #Get user row 
    user_profile_response = db.read_profile(student_id, "matches")
    if user_profile_response is None:
        user_profile_response = {}
    #TODO: Check if recco is empty, wait for update
    recco_student_id = user_profile_response.get("recco_student_id")
    #print(f"recco: {recco_student_id}")

    if isinstance(recco_student_id, str):
        recco_student_id = json.loads(recco_student_id)

    if not recco_student_id: #Check if current recco_student_id is empty
        populate_result = profile_matching_AI.populate_recco_list(student_id)
        if populate_result["status"] != 200:
            return {"success": False, "error": "Error in finding a match"}
        recco_student_id = populate_result["reccomendations"]
    
    sorted_recco_id = sort_matches_by_score(user_profile_response["recco_student_id"])
    for student_id, compatability in sorted_recco_id:
        if student_id in user_profile_response["accepted_student_id"] or student_id in user_profile_response["rejected_student_id"]:
            continue
        return {"success": True, "student_id": student_id, "compatability": compatability}
    return {"success": False, "error": "Out of reccomended students"}

def get_next_match(matches, current_index):
    """Get the next match from the list of matches."""
    if current_index < len(matches):
        return matches[current_index]
    return None

# ===== testing space :) ======

# #while current_match < len(parsed_matches):
#     show_next_match(parsed_matches)

#     user_input = input("\nPress N to see the next match: ")

#     if user_input.lower() != "n":
#         print("Please press N to continue.")

def main(id):
    matches = load_matches(id)

    if not matches:
        print("No matches found.")
        return

    for student_id, score in matches.items():
        print("\n--------------------")
        print(f"Student ID: {student_id}")
        print(f"Score: {score}")

        details = db.read_profile(student_id, sheet_name="users")
        print("Details:", details)

        while True:
            choice = input("Accept or Reject? ").strip().lower()

            if choice == "accept":
                add_accepted_match(id, student_id)
                is_mutual = is_mutual_match(id, student_id)
                if is_mutual:
                    print(f"{student_id} accepted and it's a mutual match!")
                print(f"{student_id} accepted")
                break
            elif choice == "reject":
                add_rejected_match(id, student_id)
                print(f"{student_id} rejected")
                break
            else:
                print("Please type 'accept' or 'reject'.")
if __name__ == "__main__":
    test = load_matches("1001")
    if test:
        print(sort_matches_by_score(test))