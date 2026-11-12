"""Run: py -m unittest discover -s tests -p test_birthday_privacy.py -v"""
from datetime import date
import unittest
from Logic_Manager.profile_logic_manager import ProfileLogicManager
from Logic_Manager import logic_manager
from sitogether_app import SITogetherApp
from config.user_fields import USER_FIELD_CONFIG, PROFILE_FIELDS
from models.dealbreaker import DealBreaker


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

    def test_existing_wrapper(self):
        self.assertEqual(logic_manager.process_birthday("09/11/2005", date(2026, 11, 12))["age"],21)

    def test_persisted_values_do_not_include_birthday(self):
        app = SITogetherApp(
            None, None, None, None, None, None, self.logic,
            USER_FIELD_CONFIG, PROFILE_FIELDS, DealBreaker
        )
        values = app._storage_values({
            "birthday": "09/11/2005",
            "name": "Student", "match_preference": "Both",
        })
        self.assertNotIn("birthday", values)
        self.assertEqual(values["horoscope"], "Scorpio")
        self.assertIn("age", values)

    def test_existing_user_not_reprompted(self):
        app = SITogetherApp(
            None, None, None, None, None, None, self.logic,
            USER_FIELD_CONFIG, PROFILE_FIELDS, DealBreaker
        )
        questions = app._questions_for_profile({"age": 21, "horoscope": "Scorpio"})
        self.assertNotIn("birthday", [question["key"] for question in questions])

if __name__ == "__main__":
    unittest.main()
