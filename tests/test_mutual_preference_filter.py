"""No database or AI credentials required: python -m unittest tests.test_mutual_preference_filter"""

import unittest

from Logic_Manager.Matching.mutual_preference_filter import MutualPreferenceFilter
from models.user import User


class TestMutualPreferenceFilter(unittest.TestCase):
    def setUp(self):
        self.f = MutualPreferenceFilter()
        self.a = User(student_id="A", gender="Male", match_preference="Female", age=21,
                      religion="None", race="Chinese")

    def test_male_to_female_and_female_to_female_rejected(self):
        b = User(student_id="B", gender="Female", match_preference="Female", age=20)
        self.assertFalse(self.f.is_eligible(self.a, b))
        self.assertFalse(self.f.is_eligible(b, self.a))

    def test_male_to_female_and_female_to_male_accepted(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=20)
        self.assertTrue(self.f.is_eligible(self.a, c))

    def test_males_excluded_when_a_wants_females(self):
        d = User(student_id="D", gender="Male", match_preference="Female", age=21)
        self.assertFalse(self.f.is_eligible(self.a, d))

    def test_both_allows_gender_if_other_side_agrees(self):
        c = User(student_id="C", gender="Female", match_preference="Both", age=20)
        self.assertTrue(self.f.is_eligible(self.a, c))

    def test_reverse_age_restriction(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=20)
        self.assertFalse(self.f.is_eligible(self.a, c, None, {"min_age": 22}))

    def test_forward_age_restriction(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=25)
        self.assertFalse(self.f.is_eligible(self.a, c, {"max_age": 23}))

    def test_reverse_race_blacklist(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=20)
        self.assertFalse(self.f.is_eligible(self.a, c, None, {"race": ["Chinese"]}))

    def test_forward_religion_blacklist(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=20,
                 religion="Buddhism")
        self.assertFalse(self.f.is_eligible(self.a, c, {"religion": ["Buddhism"]}))

    def test_no_preference_is_not_blacklist(self):
        c = User(student_id="C", gender="Female", match_preference="Male", age=20,
                 religion="Buddhism")
        self.assertTrue(self.f.is_eligible(self.a, c, {"religion": ["No preference"]}))

    def test_self_excluded(self):
        self.assertFalse(self.f.is_eligible(self.a, self.a))


if __name__ == "__main__":
    unittest.main()
