"""SITogether Match Outcomes / Logic Manager.

This module contains the match-outcome business rules and talks to the
existing `matches.py` database wrapper.

It does NOT modify match.py.
"""

import json


VALID_DECISIONS = ("accept", "reject")


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


def _database():
    """Import matches.py only when a database function is actually needed.

    This keeps the pure logic importable during offline testing.
    """
    import matches
    return matches


def _normalise_id_list(value):
    """Convert a database value into a clean list of student IDs."""
    if value is None or value == "":
        return []

    if isinstance(value, list):
        items = value

    elif isinstance(value, tuple):
        items = list(value)

    elif isinstance(value, str):
        text = value.strip()

        if not text:
            return []

        try:
            parsed = json.loads(text)
            items = parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            # Also accepts an older value such as: 1008, 1007
            items = [item.strip() for item in text.split(",")]

    else:
        items = [value]

    cleaned = []

    for item in items:
        student_id = str(item).strip()

        if student_id and student_id not in cleaned:
            cleaned.append(student_id)

    return cleaned


def _normalise_recommendations(value):
    """Convert the recommendation field into {student_id: score}."""
    if value is None or value == "":
        return {}

    if isinstance(value, dict):
        raw = value

    elif isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}

        if not isinstance(parsed, dict):
            return {}

        raw = parsed

    else:
        return {}

    recommendations = {}

    for student_id, score in raw.items():
        try:
            score = int(score)
        except (TypeError, ValueError):
            continue

        if 0 <= score <= 100:
            recommendations[str(student_id)] = score

    return recommendations


def get_recommendations(student_id):
    """Read a student's recommendations through the existing matches.py."""
    db = _database()
    result = db.get_recco_student_id(str(student_id))

    if not isinstance(result, dict) or not result.get("success"):
        return {
            "success": False,
            "recommendations": {},
            "error": (
                result.get("error", "Unable to get recommendations")
                if isinstance(result, dict)
                else "Unable to get recommendations"
            ),
        }

    recommendations = _normalise_recommendations(
        result.get("recco_student_id")
    )

    return {
        "success": True,
        "recommendations": recommendations,
    }


def sort_recommendations(recommendations):
    """Sort {student_id: score} from highest to lowest score."""
    recommendations = _normalise_recommendations(recommendations)

    result = []

    for student_id, score in recommendations.items():
        result.append({
            "student_id": student_id,
            "score": score,
            "label": compatibility_label(score),
        })

    return sorted(
        result,
        key=lambda item: item["score"],
        reverse=True,
    )


def get_accepted_students(student_id):
    """Read one student's accepted list through matches.py."""
    db = _database()
    result = db.get_accepted_match(str(student_id))

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

    accepted = _normalise_id_list(
        result.get("accepted_student_id")
    )

    return {
        "success": True,
        "accepted_student_id": accepted,
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

    db = _database()

    # Do not add the same student twice if the database already has it.
    current = get_accepted_students(decision["student_id"])

    if not current["success"]:
        return current

    if decision["target_id"] not in current["accepted_student_id"]:
        result = db.add_accepted_match(
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
    removed = db.remove_recco_student_id(
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

    db = _database()

    # If this user had accepted before, Reject should override that choice.
    current = get_accepted_students(decision["student_id"])

    if current["success"] and (
        decision["target_id"] in current["accepted_student_id"]
    ):
        removed_accept = db.remove_accepted_match(
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

    result = db.add_rejected_match(
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

    removed = db.remove_recco_student_id(
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
