"""Offline tests for match_outcomes.py.

This test replaces matches.py with a fake in-memory module,
so it does NOT connect to Google Sheets.

Run:
    python test_match_logic.py
"""

import sys
from types import ModuleType


fake_matches = ModuleType("matches")

RECOMMENDATIONS = {
    "1001": {"1008": 78, "1007": 65, "1004": 64},
    "1008": {"1001": 86},
}

ACCEPTED = {
    "1001": [],
    "1008": [],
}

REJECTED = {
    "1001": [],
    "1008": [],
}


def add_recco_student_id(student_id, new_students):
    RECOMMENDATIONS.setdefault(str(student_id), {}).update(new_students)
    return {"success": True, "status": 200}


def remove_recco_student_id(student_id, students_to_remove):
    recommendations = RECOMMENDATIONS.setdefault(str(student_id), {})

    for target in students_to_remove:
        recommendations.pop(str(target), None)

    return {"success": True, "status": 200}


def get_recco_student_id(student_id):
    return {
        "success": True,
        "recco_student_id": RECOMMENDATIONS.get(str(student_id), {}),
    }


def add_accepted_match(student_id, new_matches):
    values = ACCEPTED.setdefault(str(student_id), [])

    for target in new_matches:
        target = str(target)

        if target not in values:
            values.append(target)

    return {"success": True, "status": 200}


def remove_accepted_match(student_id, matches_to_remove):
    values = ACCEPTED.setdefault(str(student_id), [])

    for target in matches_to_remove:
        target = str(target)

        if target in values:
            values.remove(target)

    return {"success": True, "status": 200}


def get_accepted_match(student_id):
    return {
        "success": True,
        "accepted_student_id": ACCEPTED.get(str(student_id), []),
    }


def add_rejected_match(student_id, new_matches):
    values = REJECTED.setdefault(str(student_id), [])

    for target in new_matches:
        target = str(target)

        if target not in values:
            values.append(target)

    return {"success": True, "status": 200}


fake_matches.add_recco_student_id = add_recco_student_id
fake_matches.remove_recco_student_id = remove_recco_student_id
fake_matches.get_recco_student_id = get_recco_student_id
fake_matches.add_accepted_match = add_accepted_match
fake_matches.remove_accepted_match = remove_accepted_match
fake_matches.get_accepted_match = get_accepted_match
fake_matches.add_rejected_match = add_rejected_match

sys.modules["matches"] = fake_matches

import match_outcomes


def run_tests():
    # Compatibility
    assert match_outcomes.compatibility_label(94) == "High Compatibility"
    assert match_outcomes.compatibility_label(80) == "Moderate Compatibility"
    assert match_outcomes.compatibility_label(65) == "Low Compatibility"

    # Recommendations come from matches.py and are sorted
    result = match_outcomes.get_recommendations("1001")
    assert result["success"]

    sorted_matches = match_outcomes.sort_recommendations(
        result["recommendations"]
    )

    assert [item["student_id"] for item in sorted_matches] == [
        "1008",
        "1007",
        "1004",
    ]

    # 1001 accepts 1008 -> waiting
    outcome = match_outcomes.handle_match_decision(
        "1001",
        "1008",
        "accept",
    )

    assert outcome["status"] == "waiting"
    assert ACCEPTED["1001"] == ["1008"]
    assert "1008" not in RECOMMENDATIONS["1001"]

    # 1008 accepts 1001 -> both accepted -> matched
    outcome = match_outcomes.handle_match_decision(
        "1008",
        "1001",
        "accept",
    )

    assert outcome["status"] == "matched"
    assert outcome["release_contact"] is True
    assert match_outcomes.is_mutual_match("1001", "1008")

    # Reject overrides a previous accept
    outcome = match_outcomes.handle_match_decision(
        "1001",
        "1008",
        "reject",
    )

    assert outcome["status"] == "rejected"
    assert "1008" not in ACCEPTED["1001"]
    assert "1008" in REJECTED["1001"]

    # Invalid choices fail safely
    outcome = match_outcomes.handle_match_decision(
        "1001",
        "1007",
        "maybe",
    )

    assert outcome["status"] == "error"

    print("All match outcome tests passed.")


if __name__ == "__main__":
    run_tests()
