import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from . import matches
from database import db

VALID_DECISIONS = ("accept", "reject")
current_match = 0

def load_matches(id):
    recco_ids = matches.get_user_recco_student_id(id)
    return recco_ids["recco_student_id"]

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

def parse_ai_matches(matches_dict): #seperates the matches for iteration
    return [
        (student_id, score)
        for student_id, score in matches_dict.items()
    ]

def show_next_match(matches):
    global current_match

    if current_match >= len(matches):
        return False

    student_id, compatibility = matches[current_match]
    current_match += 1
    target_id = matches.read_profile(student_id, sheet_name="users")
    return target_id, compatibility

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

    accepted = parse_ai_matches(
        result.get("accepted_student_id")
    )

    return {
        "success": True,
        "accepted_student_id": accepted,
    }

def is_mutual_match(student_id, target_id):
    """Return True only when both students accepted each other."""
    student_id = str(student_id)
    target_id = str(target_id)

    first = get_accepted_students(student_id)
    second = get_accepted_students(target_id)

    if not first["success"] or not second["success"]:
        return False

    return (
        target_id in first["accepted_student_id"]
        and student_id in second["accepted_student_id"]
    )

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


# ===== testing space :) ======

parsed_matches = parse_ai_matches(load_matches("1001")) 

while current_match < len(parsed_matches):
    show_next_match(parsed_matches)

    user_input = input("\nPress N to see the next match: ")

    if user_input.lower() != "n":
        print("Please press N to continue.")

def main(id):
    matches = matches.get_user_recco_student_id(id)

    accepted = []
    rejected = []

    if not matches:
        print("No matches found.")
        return

    for student_id, score in matches.items():
        print("\n--------------------")
        print(f"Student ID: {student_id}")
        print(f"Score: {score}")

        details = matches.read_profile(student_id, sheet_name="profiles")
        print("Details:", details)

        while True:
            choice = input("Accept or Reject? ").strip().lower()

            if choice == "accept":
                accepted.append(student_id)
                print(f"{student_id} accepted")
                break
            elif choice == "reject":
                rejected.append(student_id)
                print(f"{student_id} rejected")
                break
            else:
                print("Please type 'accept' or 'reject'.")
