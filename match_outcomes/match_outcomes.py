"""SITogether Logic Manager: business rules for match outcomes.

This module contains only procedural, testable business rules.
It deliberately does not print, read input, call Telegram, call the AI API,
or write files/Google Sheets.
"""

VALID_DECISIONS = ("accept", "reject")


def compatibility_label(score):
    """Convert an AI compatibility score into the team's score band."""
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


def sort_matches(matches):
    """Return AI match records sorted from highest to lowest score.

    Expected record example:
    {
        "student_id": "2601973",
        "compatibility_score": 80,
        "common_points": ["Gaming", "Anime"]
    }

    Invalid records are ignored instead of crashing the program.
    """
    cleaned = []

    for match in matches or []:
        if not isinstance(match, dict):
            continue

        student_id = str(match.get("student_id", "")).strip()
        score = match.get("compatibility_score", match.get("score"))
        label = compatibility_label(score)

        if not student_id or label is None:
            continue

        record = match.copy()
        record["student_id"] = student_id
        record["compatibility_score"] = int(score)
        record["compatibility_label"] = label
        cleaned.append(record)

    return sorted(cleaned, key=lambda item: item["compatibility_score"], reverse=True)


def is_featured_recommendation(match):
    """Example multi-condition rule using two AI output fields.

    A recommendation is 'featured' only when the AI score is high AND the
    AI identified at least one highlighted common point. This does not change
    the team's official compatibility bands; it is an optional display flag.
    """
    if not isinstance(match, dict):
        return False

    score = match.get("compatibility_score", match.get("score"))
    common_points = match.get("common_points", [])

    try:
        score = int(score)
    except (TypeError, ValueError):
        return False

    return score >= 85 and isinstance(common_points, list) and len(common_points) > 0


def create_match_decision(user_id, target_id, decision):
    """Validate and create one directional Accept/Reject decision."""
    user_id = str(user_id).strip()
    target_id = str(target_id).strip()
    decision = str(decision).strip().lower()

    if not user_id or not target_id or user_id == target_id:
        return None
    if decision not in VALID_DECISIONS:
        return None

    return {
        "from_user": user_id,
        "to_user": target_id,
        "decision": decision,
    }


def upsert_match_decision(actions, new_action):
    """Insert a decision or replace the user's previous decision for that person.

    This also makes repeated Telegram button taps safe because one directional
    pair has at most one current decision.
    """
    if not isinstance(new_action, dict):
        return list(actions or [])

    replacement = create_match_decision(
        new_action.get("from_user"),
        new_action.get("to_user"),
        new_action.get("decision"),
    )
    if replacement is None:
        return list(actions or [])

    updated = []
    for action in actions or []:
        if not isinstance(action, dict):
            continue
        same_direction = (
            str(action.get("from_user")) == replacement["from_user"]
            and str(action.get("to_user")) == replacement["to_user"]
        )
        if not same_direction:
            updated.append(action.copy())

    updated.append(replacement)
    return updated


def get_decision(actions, user_id, target_id):
    """Return a user's current decision about another user, or None."""
    user_id = str(user_id)
    target_id = str(target_id)

    # Search from the end so this still works safely with old duplicate records.
    for action in reversed(actions or []):
        if not isinstance(action, dict):
            continue
        if (
            str(action.get("from_user")) == user_id
            and str(action.get("to_user")) == target_id
        ):
            decision = str(action.get("decision", "")).lower()
            return decision if decision in VALID_DECISIONS else None

    return None


def has_accepted(actions, user_id, target_id):
    return get_decision(actions, user_id, target_id) == "accept"


def has_rejected(actions, user_id, target_id):
    return get_decision(actions, user_id, target_id) == "reject"


def is_mutual_match(actions, user_a, user_b):
    """A match exists only when BOTH users currently accepted each other."""
    return (
        has_accepted(actions, user_a, user_b)
        and has_accepted(actions, user_b, user_a)
    )


def pair_has_rejection(actions, user_a, user_b):
    """True when either person rejected the other."""
    return (
        has_rejected(actions, user_a, user_b)
        or has_rejected(actions, user_b, user_a)
    )


def can_recommend(actions, current_user_id, candidate_id):
    """Apply SITogether rules before showing a candidate again.

    Excludes:
    - the user themself;
    - anyone already rejected in either direction;
    - an existing mutual match;
    - anyone this user already accepted (waiting for the other person's reply),
      so the same profile is not repeatedly shown.
    """
    current_user_id = str(current_user_id)
    candidate_id = str(candidate_id)

    if not current_user_id or not candidate_id or current_user_id == candidate_id:
        return False
    if pair_has_rejection(actions, current_user_id, candidate_id):
        return False
    if is_mutual_match(actions, current_user_id, candidate_id):
        return False
    if has_accepted(actions, current_user_id, candidate_id):
        return False

    return True


def filter_recommendations(ai_matches, actions, current_user_id):
    """Sort AI results and remove candidates that should not be shown."""
    result = []

    for match in sort_matches(ai_matches):
        if can_recommend(actions, current_user_id, match["student_id"]):
            match["featured"] = is_featured_recommendation(match)
            result.append(match)

    return result


def get_match_outcome(actions, user_id, target_id):
    """Return the match state that the UI/Telegram layer should display."""
    decision = get_decision(actions, user_id, target_id)

    if decision == "reject":
        return {
            "status": "rejected",
            "matched": False,
            "release_contact": False,
        }

    if is_mutual_match(actions, user_id, target_id):
        return {
            "status": "matched",
            "matched": True,
            "release_contact": True,
        }

    if decision == "accept":
        return {
            "status": "waiting",
            "matched": False,
            "release_contact": False,
        }

    return {
        "status": "no_decision",
        "matched": False,
        "release_contact": False,
    }
