"""Run: py -m unittest discover -s tests -p test_birthday_privacy.py -v"""
from datetime import date
import unittest
from Logic_Manager.profile_logic_manager import ProfileLogicManager
from IO_Manager.profile_form import ProfileForm
from config.user_fields import PROFILE_FIELDS


class BirthdayPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.logic = ProfileLogicManager(PROFILE_FIELDS)

    def test_normal_birthday(self):
        self.assertEqual(
            self.logic.process_birthday("09/11/2005", today=date(2026, 11, 12)),
            {"age": 21, "horoscope": "Scorpio"},
        )

    def test_before_birthday(self):
        self.assertEqual(
            self.logic.process_birthday("13/11/2005", today=date(2026, 11, 12))["age"], 20
        )

    def test_sign_boundaries(self):
        for raw, expected in (
            ("19/01/2000", "Capricorn"), ("20/01/2000", "Aquarius"),
            ("20/03/2000", "Pisces"), ("21/03/2000", "Aries"),
            ("21/12/2000", "Sagittarius"), ("22/12/2000", "Capricorn"),
            ("29/02/2004", "Pisces"),
        ):
            with self.subTest(raw=raw):
                self.assertEqual(self.logic.process_birthday(raw)["horoscope"], expected)

    def test_bad_date(self):
        with self.assertRaises(ValueError):
            self.logic.process_birthday("31/02/2005")

    def test_birthday_is_saved_as_date_with_derived_values(self):
        form = ProfileForm(logic=self.logic)
        values = form.storage_values({
            "birthday": "09/11/2005",
            "name": "Student", "match_preference": "Both",
        })
        self.assertEqual(values["birthday"], date(2005, 11, 9))
        self.assertEqual(values["horoscope"], "Scorpio")
        self.assertIn("age", values)

    def test_stored_birthday_loads_into_edit_form(self):
        from models.profile import Profile
        loaded = Profile.from_dict({"student_id": "A", "birthday": date(2005, 6, 15)})
        self.assertEqual(ProfileForm().form_values(loaded)["birthday"], "15/06/2005")

    def test_birthday_is_excluded_from_both_ai_prompts(self):
        from models.user import User
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        user = User(student_id="A", birthday=date(2005, 6, 15), bio="Coding")
        data = GroqScorer(None)._to_ai_dict(user)
        self.assertNotIn("birthday", data)
        prompt = SuggestionsGenerator(None)._build_prompt(user.get_user_details(), user.get_user_details())
        self.assertNotIn("2005-06-15", prompt)
        self.assertNotIn("birthday:", prompt)

    def test_existing_user_not_reprompted(self):
        form = ProfileForm(logic=self.logic)
        questions = form.questions_for_profile({"age": 21, "horoscope": "Scorpio"})
        self.assertNotIn("birthday", [question["key"] for question in questions])

if __name__ == "__main__":
    unittest.main()
