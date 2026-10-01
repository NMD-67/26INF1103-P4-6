"""Offline tests for SITogether match-outcome business logic.

Run with:
    python test_match_logic.py

No AI API, Telegram bot, Google Sheets, or internet connection is required.
"""

import match_outcomes


def run_tests():
    # Compatibility bands
    assert match_outcomes.compatibility_label(94) == "High Compatibility"
    assert match_outcomes.compatibility_label(85) == "High Compatibility"
    assert match_outcomes.compatibility_label(84) == "Moderate Compatibility"
    assert match_outcomes.compatibility_label(70) == "Moderate Compatibility"
    assert match_outcomes.compatibility_label(69) == "Low Compatibility"
    assert match_outcomes.compatibility_label(101) is None

    # AI match sorting + multi-condition featured rule
    ai_matches = [
        {"student_id": "B", "compatibility_score": 80, "common_points": ["Anime"]},
        {"student_id": "A", "compatibility_score": 94, "common_points": ["Games", "Running"]},
        {"student_id": "C", "compatibility_score": 60, "common_points": []},
    ]
    sorted_matches = match_outcomes.sort_matches(ai_matches)
    assert [item["student_id"] for item in sorted_matches] == ["A", "B", "C"]
    assert match_outcomes.is_featured_recommendation(sorted_matches[0]) is True
    assert match_outcomes.is_featured_recommendation(sorted_matches[1]) is False

    # One-sided accept -> waiting, do not release handle
    actions = []
    first = match_outcomes.create_match_decision("1111111", "2222222", "accept")
    actions = match_outcomes.upsert_match_decision(actions, first)
    assert match_outcomes.is_mutual_match(actions, "1111111", "2222222") is False
    outcome = match_outcomes.get_match_outcome(actions, "1111111", "2222222")
    assert outcome == {"status": "waiting", "matched": False, "release_contact": False}

    # Reciprocal accept -> match, release handle allowed
    second = match_outcomes.create_match_decision("2222222", "1111111", "accept")
    actions = match_outcomes.upsert_match_decision(actions, second)
    assert match_outcomes.is_mutual_match(actions, "1111111", "2222222") is True
    outcome = match_outcomes.get_match_outcome(actions, "1111111", "2222222")
    assert outcome == {"status": "matched", "matched": True, "release_contact": True}

    # Existing matches are not recommended again
    assert match_outcomes.can_recommend(actions, "1111111", "2222222") is False

    # Reject -> no match and recommendation excluded
    reject_actions = []
    rejection = match_outcomes.create_match_decision("3333333", "4444444", "reject")
    reject_actions = match_outcomes.upsert_match_decision(reject_actions, rejection)
    assert match_outcomes.pair_has_rejection(reject_actions, "3333333", "4444444") is True
    assert match_outcomes.can_recommend(reject_actions, "3333333", "4444444") is False
    outcome = match_outcomes.get_match_outcome(reject_actions, "3333333", "4444444")
    assert outcome == {"status": "rejected", "matched": False, "release_contact": False}

    # Repeated/changed decision replaces the old one instead of duplicating it
    changed = match_outcomes.create_match_decision("3333333", "4444444", "accept")
    reject_actions = match_outcomes.upsert_match_decision(reject_actions, changed)
    assert len(reject_actions) == 1
    assert match_outcomes.get_decision(reject_actions, "3333333", "4444444") == "accept"

    # Invalid inputs fail safely
    assert match_outcomes.create_match_decision("1", "1", "accept") is None
    assert match_outcomes.create_match_decision("1", "2", "maybe") is None

    print("All match logic tests passed.")


if __name__ == "__main__":
    run_tests()
