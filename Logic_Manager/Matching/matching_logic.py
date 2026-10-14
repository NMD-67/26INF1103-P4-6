import json
from re import match
import sys
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

TEST_USERS_FILE = os.path.join(BASE_DIR, "test_users.json")
TEST_AI_FILE = os.path.join(BASE_DIR, "test_ai_output.json")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from AI_Manager import profile_matching_AI
from src import matches 
from src.matches import add_accepted_match, add_rejected_match, get_accepted_match, get_rejected_match
from Data_Manager.database import db



VALID_DECISIONS = ("accept", "reject")
current_match = 0

def load_json_file(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)

def load_matches(id, test_mode=False, ai_file=TEST_AI_FILE):
    if test_mode:
        ai_data = load_json_file(ai_file)
        recco_ids = ai_data.get(str(id))
    else:
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
        return "High Compatibility"
    if score >= 70:
        return "Moderate Compatibility"
    return "Low Compatibility"

def show_next_match(match_dict):
    global current_match

    if current_match >= len(match_dict):
        return False

    student_id, compatibility = list(match_dict.items())[current_match]
    current_match += 1
    target_id = matches.read_profile(student_id, sheet_name="users")
    return target_id, compatibility

def check_user_decision(decision):
    return decision.lower() in VALID_DECISIONS

def get_accepted_students(student_id, test_mode=False, users_file="test_users.json"):
    if test_mode:
        users_data = load_json_file(users_file)
        accepted = users_data.get("accepted_matches", {}).get(str(student_id), [])
        return {
            "success": True,
            "accepted_student_id": accepted,
        }

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

    return {
        "success": True,
        "accepted_student_id": result.get("accepted_student_id", []),
    }

def is_mutual_match(student_id, target_id, accepted_ids=None):
    """Check whether both students have accepted each other."""
    student_id = str(student_id).strip()
    target_id = str(target_id).strip()

    # Read your accepted list only if it was not already provided.
    if accepted_ids is None:
        first = get_accepted_students(student_id)

        if not first["success"]:
            raise RuntimeError(
                "Could not read your accepted matches. Please try again later."
            )

        accepted_ids = first["accepted_student_id"]

    accepted_ids = [str(value).strip() for value in accepted_ids]

    # There cannot be a mutual connection if you have not accepted them.
    if target_id not in accepted_ids:
        return False

    # Check whether the other student has accepted you.
    second = get_accepted_students(target_id)

    if not second["success"]:
        raise RuntimeError(
            "Could not check the other student's accepted matches. "
            "Please try again later."
        )

    target_accepted_ids = [
        str(value).strip()
        for value in second["accepted_student_id"]
    ]

    return student_id in target_accepted_ids

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
    if not current["success"]:
        return current

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
    """Sort matches by score in descending order."""
    return sorted(match_dict.items(), key=lambda x: x[1], reverse=True)

def get_next_user(student_id: str):
    student_id = str(student_id)

    user_profile = db.read_profile(student_id, "matches")

    if user_profile is None:
        user_profile = {}

    recommendations = user_profile.get("recco_student_id") or {}

    # Convert spreadsheet JSON text into a dictionary.
    if isinstance(recommendations, str):
        recommendations = json.loads(recommendations)

    # Generate recommendations if none are saved.
    if not recommendations:
        result = profile_matching_AI.populate_recco_list(student_id)

        if not result["success"]:
            return {
                "success": False,
                "error": "Could not generate recommendations. Please try again later."
            }

        # Reload the record because the AI function saved new recommendations.
        user_profile = db.read_profile(student_id, "matches")

        if user_profile is None:
            return {
                "success": False,
                "error": "Could not find your matching record."
            }

        recommendations = user_profile.get("recco_student_id") or {}

        if isinstance(recommendations, str):
            recommendations = json.loads(recommendations)

    accepted = user_profile.get("accepted_student_id") or []
    rejected = user_profile.get("rejected_student_id") or []

    if isinstance(accepted, str):
        accepted = json.loads(accepted)

    if isinstance(rejected, str):
        rejected = json.loads(rejected)

    accepted = [str(value) for value in accepted]
    rejected = [str(value) for value in rejected]

    sorted_recommendations = sort_matches_by_score(recommendations)

    for target_id, compatibility in sorted_recommendations:
        target_id = str(target_id)

        if target_id == student_id:
            continue

        if target_id in accepted or target_id in rejected:
            continue

        return {
            "success": True,
            "student_id": target_id,
            "compatability": compatibility
        }

    return {
        "success": False,
        "error": "Out of recommended students."
    }   

def get_next_match(match_list, current_index):
    """Get the next match from the list of matches."""
    if current_index < len(match_list):
        return match_list[current_index]
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
    test = load_matches("9000001", test_mode=True)
    print(test)


# sorted_matches = sort_matches_by_score(test)
# print(sorted_matches)

