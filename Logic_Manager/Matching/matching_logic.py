"""Backward-compatible matching functions powered by OOP classes.

Uses the original SITogether Data_Manager/database/db.py and src/matches.py.
No additional database connection is needed.
"""

import json
from pathlib import Path

from Data_Manager.database import db
from .recommendation_manager import RecommendationManager
from .match_decision_manager import MatchDecisionManager
from .mutual_match_checker import MutualMatchChecker

_recommendations = RecommendationManager()
_decisions = MatchDecisionManager()
_mutual = MutualMatchChecker()
current_match = 0


def load_json_file(file_path):
    with open(file_path, encoding="utf-8") as file:
        return json.load(file)


def load_matches(student_id, test_mode=False, ai_file=None):
    if test_mode:
        if ai_file is None:
            ai_file = Path(__file__).resolve().parents[2] / "test_ai_output.json"
        data = load_json_file(ai_file)
        return data.get(str(student_id))
    return _recommendations.load_matches(student_id)


def compatibility_label(score):
    return RecommendationManager.compatibility_label(score)


def sort_matches_by_score(match_dict):
    return RecommendationManager.sort_matches_by_score(match_dict)


def get_next_match(match_list, current_index):
    return RecommendationManager.get_next_match(match_list, current_index)


def get_next_user(student_id):
    return _recommendations.get_next_user(student_id)


def show_next_match(match_dict):
    global current_match
    candidate = get_next_match(list(match_dict.items()), current_match)
    if candidate is None:
        return False
    current_match += 1
    student_id, compatibility = candidate
    return db.read_profile(student_id, sheet_name="users"), compatibility


def check_user_decision(decision):
    return MatchDecisionManager.check_user_decision(decision)


def create_match_decision(student_id, target_id, decision):
    return _decisions.create_match_decision(student_id, target_id, decision)


def record_accept(student_id, target_id):
    return _decisions.record_accept(student_id, target_id)


def record_reject(student_id, target_id):
    return _decisions.record_reject(student_id, target_id)


def get_accepted_students(student_id, test_mode=False, users_file="test_users.json"):
    if test_mode:
        data = load_json_file(users_file)
        return {
            "success": True,
            "accepted_student_id": data.get("accepted_matches", {}).get(str(student_id), []),
        }
    return _mutual.get_accepted_students(student_id)


def is_mutual_match(student_id, target_id):
    return _mutual.is_mutual_match(student_id, target_id)


def handle_match_decision(student_id, target_id, decision):
    return _decisions.handle_match_decision(student_id, target_id, decision)


def main(student_id):
    """Retain the old command-line test helper; not run during import."""
    recommendations = load_matches(student_id)
    if not recommendations:
        print("No matches found.")
        return

    for candidate_id, score in recommendations.items():
        print(f"Student ID: {candidate_id} | Score: {score}")
        print("Details:", db.read_profile(candidate_id, sheet_name="users"))
        while True:
            decision = input("Accept or Reject? ").strip().lower()
            if check_user_decision(decision):
                print(handle_match_decision(student_id, candidate_id, decision)["status"])
                break
            print("Please type 'accept' or 'reject'.")
