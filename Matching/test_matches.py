import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import db

def test_retrieve_matches(id):
    match = db.get_user_recco_student_id(id)
    print(match)

test_retrieve_matches("1001")