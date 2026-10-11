import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import db

# logic 
# user log in
# user request for matches
# call ai function to get matches
# Give matches (my part)
# one by one recieve accept or reject from user
# then update db
# check if both users have accepted each other, if yes then update db to match them
# give the matches to the user
# and also the ai function to give convo starters

def test_retrieve_matches(id):
    recco_ids = db.get_user_recco_student_id("1001")
    return recco_ids["recco_student_id"]

def main(id):
    matches = db.get_user_recco_student_id(id)

    accepted = []
    rejected = []

    if not matches:
        print("No matches found.")
        return

    for student_id, score in matches.items():
        print("\n--------------------")
        print(f"Student ID: {student_id}")
        print(f"Score: {score}")

        details = db.read_profile(student_id, sheet_name="profiles")
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


# ====== TESTING FUNCTIONS ======

matches = test_retrieve_matches("1001")
print(matches.items())
