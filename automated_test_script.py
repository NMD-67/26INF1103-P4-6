"""INF1103 automated core-logic checks (procedural, offline).

Put beside main.py: python automated_core_tests.py
Or: python automated_core_tests.py --project "C:/path/to/project"

Uses real functions and hardcoded data. No interactive input, email, API keys,
or spreadsheet writes. Dependencies from requirements.txt must be installed.
Exit status: 0 = every check passed; 1 = failures or unexpected errors.
"""

import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import date
from importlib import import_module
from io import StringIO
import json
from pathlib import Path
import sys
from unittest.mock import patch


# Fixed samples replace the outputs of a live AI service.
SAMPLE_AI_SCORES = '{"9000002": 60, "9000003": 95, "9000004": 75}'
SAMPLE_AI_SUGGESTIONS = {
    "common_interests": [" Coding "],
    "conversation_starters": ["What project are you working on?"],
    "outing_ideas": ["Attend a campus technology event."],
}


def profile_logic():
    return import_module("Logic_Manager.logic_manager")


def match_logic():
    return import_module("Logic_Manager.Matching.matching_logic")


def expect_value_error(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("Expected invalid input to raise ValueError")


def test_valid_birthday():
    assert profile_logic().parse_birthday("29/02/2024") == date(2024, 2, 29)


def test_invalid_birthday():
    expect_value_error(lambda: profile_logic().parse_birthday("29/02/2023"))


def test_skip_rule():
    field = {"skip_if": {"field": "here_for", "in": ["Friends"]}}
    assert profile_logic().should_skip_field({"here_for": "Friends"}, field)
    assert not profile_logic().should_skip_field({"here_for": "Relationship"}, field)
    assert not profile_logic().should_skip_field({}, {"key": "name"})


def test_missing_required_fields():
    fields = [
        {"key": "name", "required": True},
        {"key": "hobbies", "required": True},
        {"key": "bio", "required": False},
    ]
    profile = {"name": "   ", "hobbies": [None, "", "  "]}
    missing = profile_logic().find_missing_fields(profile, fields)
    assert [field["key"] for field in missing] == ["name", "hobbies"]


def test_profile_completeness():
    fields = [
        {"key": "name", "required": True},
        {"key": "hobbies", "required": True},
        {"key": "bio", "required": False},
    ]
    assert profile_logic().is_profile_complete(
        {"name": "Sample Student", "hobbies": ["Reading"]}, fields
    )
    assert not profile_logic().is_profile_complete(
        {"name": "Sample Student", "hobbies": []}, fields
    )


def test_clear_fields():
    profile = {"hobbies": ["Reading"], "bio": "Old text"}
    profile_logic().clear_field(profile, {"key": "hobbies", "kind": "list"})
    profile_logic().clear_field(profile, {"key": "bio", "kind": "text"})
    assert profile == {"hobbies": [], "bio": None}


def test_hardcoded_ai_score_sorting():
    scores = json.loads(SAMPLE_AI_SCORES)
    expected = [("9000003", 95), ("9000004", 75), ("9000002", 60)]
    assert match_logic().sort_matches_by_score(scores) == expected
    assert match_logic().sort_matches_by_score({}) == []


def test_score_category_boundaries():
    cases = [(0, "Low"), (69, "Low"), (70, "Moderate"),
             (84, "Moderate"), (85, "High"), (100, "High")]
    for score, expected in cases:
        actual = match_logic().compatibility_label(score)
        assert actual.startswith(expected), f"Incorrect category for {score}"


def test_invalid_scores():
    for score in [-1, 101, "invalid", None]:
        assert match_logic().compatibility_label(score) is None


def test_decision_input():
    assert match_logic().check_user_decision("accept")
    assert match_logic().check_user_decision("reject")
    assert not match_logic().check_user_decision("maybe")


def test_decision_rules():
    logic = match_logic()
    assert logic.create_match_decision("9000001", "9000001", "accept") is None
    assert logic.create_match_decision("", "9000002", "accept") is None
    assert logic.create_match_decision("9000001", "9000002", "maybe") is None
    assert logic.create_match_decision("9000001", "9000002", " ACCEPT ") == {
        "student_id": "9000001", "target_id": "9000002", "decision": "accept"
    }


def test_hardcoded_ai_suggestions():
    ai = import_module("AI_Manager.matchmaking_ai")
    raw = "```json\n" + json.dumps(SAMPLE_AI_SUGGESTIONS) + "\n```"
    result = ai.validate_response(ai.parse_response(raw))
    assert result == {
        "common_interests": ["Coding"],
        "conversation_starters": ["What project are you working on?"],
        "outing_ideas": ["Attend a campus technology event."],
    }
    expect_value_error(lambda: ai.parse_response("not JSON"))
    expect_value_error(lambda: ai.validate_response({}))


def run_tests():
    tests = [
        test_valid_birthday, test_invalid_birthday, test_skip_rule,
        test_missing_required_fields, test_profile_completeness, test_clear_fields,
        test_hardcoded_ai_score_sorting, test_score_category_boundaries,
        test_invalid_scores, test_decision_input, test_decision_rules,
        test_hardcoded_ai_suggestions,
    ]
    passed = 0
    for test in tests:
        try:
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                test()
        except AssertionError as error:
            print(f"FAIL  {test.__name__}: {error or 'unexpected result'}")
        except Exception as error:
            print(f"ERROR {test.__name__}: {type(error).__name__}: {error}")
        else:
            passed += 1
            print(f"PASS  {test.__name__}")
    print(f"\nPassed: {passed} | Failed: {len(tests) - passed} | Total: {len(tests)}")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=str(Path(__file__).parent))
    args = parser.parse_args()
    project = Path(args.project).resolve()
    if not (project / "Logic_Manager" / "logic_manager.py").is_file():
        sys.exit("Put the script beside main.py, or supply --project PATH.")
    sys.path.insert(0, str(project))
    # Only service boundaries are blocked; the logic under test is never replaced.
    # These guards also expose accidental API work during module imports.
    with patch("socket.socket.connect", side_effect=RuntimeError("Live network blocked by tests")), \
         patch("socket.socket.connect_ex", side_effect=RuntimeError("Live network blocked by tests")), \
         patch("dotenv.load_dotenv", return_value=False), \
         patch("gspread.service_account", side_effect=RuntimeError("Live Sheets blocked by tests")), \
         patch("builtins.input", side_effect=RuntimeError("Automated tests cannot request input")):
        sys.exit(run_tests())
