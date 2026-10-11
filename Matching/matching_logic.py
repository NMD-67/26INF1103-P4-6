import json
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


from database import db

VALID_DECISIONS = ("accept", "reject")
current_match = 0

def load_matches(id):
    recco_ids = db.get_user_recco_student_id(id)
    return recco_ids["recco_student_id"]

def parse_ai_matches(matches_dict):
    return [
        (student_id, score)
        for student_id, score in matches_dict.items()
    ]


def show_next_match(matches):
    global current_match

    if current_match >= len(matches):
        print("No more matches available.")
        return

    student_id, compatibility = matches[current_match]
    current_match += 1
    print(f"Student ID: {student_id}, Compatibility: {compatibility}")


def check_user_decision(decision):
    return decision.lower() in VALID_DECISIONS


parsed_matches = parse_ai_matches(load_matches("1001")) #seperates the matches for iteration


while current_match < len(parsed_matches):
    show_next_match(parsed_matches)

    user_input = input("\nPress N to see the next match: ")

    if user_input.lower() != "n":
        print("Please press N to continue.")


