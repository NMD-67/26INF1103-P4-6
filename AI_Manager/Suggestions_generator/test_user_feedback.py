"""Offline tests for the student Yes/No feedback and regeneration feature."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from AI_Manager.Suggestions_generator.suggestions_generator import SuggestionsGenerator
from Logic_Manager.services.connection_suggestion_service import ConnectionSuggestionService
from models.user import User
from models.match import Match


class UserFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.viewer = User(student_id="A", course="Applied AI")
        self.matched = Match(student_id="B", course="Applied AI")
        self.items = {
            "common_interests": ["Applied AI"],
            "conversation_starters": ["What are you working on?"],
            "outing_ideas": ["Visit the library"],
        }
        self.previous = {
            "success": True, "user_a": "A", "user_b": "B",
            "user_b_info": {"name": "Bobby"},
            "compatibility": {}, **self.items,
        }

    def test_prompt_contains_feedback_and_previous_suggestions(self):
        generator = SuggestionsGenerator(primary=None)
        prompt = generator._build_prompt(
            {"course": "Applied AI"}, {"course": "Applied AI"},
            "Suggest outdoor outings", self.items,
        )
        self.assertIn("Suggest outdoor outings", prompt)
        self.assertIn("Visit the library", prompt)
        self.assertIn("JSON", prompt)

    def test_old_two_argument_prompt_still_works(self):
        generator = SuggestionsGenerator(primary=None)
        prompt = generator._build_prompt({"course": "AI"}, {"course": "AI"})
        self.assertNotIn("Previous suggestions (data", prompt)

    def make_service(self, matches=None, success=True):
        match_service = SimpleNamespace(
            get_all_matches=Mock(return_value=SimpleNamespace(
                success=success, data=[self.matched] if matches is None else matches
            ))
        )
        user_service = SimpleNamespace(
            get_user=Mock(return_value=SimpleNamespace(success=True, data=self.viewer))
        )
        generator = SimpleNamespace(generate_suggestions=Mock(return_value={
            "success": True,
            "common_interests": ["New shared course"],
            "conversation_starters": ["New question?"],
            "outing_ideas": ["New activity"],
        }))
        return ConnectionSuggestionService(match_service, user_service, generator), generator

    def test_regeneration_uses_same_match_and_feedback(self):
        service, generator = self.make_service()
        result = service.regenerate_for_connection("A", "B", "More outdoor ideas", self.previous)
        self.assertTrue(result["success"])
        self.assertEqual(result["user_b_info"]["name"], "Bobby")
        self.assertEqual(result["outing_ideas"], ["New activity"])
        generator.generate_suggestions.assert_called_once()
        self.assertEqual(generator.generate_suggestions.call_args.kwargs["review_feedback"], "More outdoor ideas")
        self.assertEqual(generator.generate_suggestions.call_args.kwargs["previous_suggestions"]["outing_ideas"], ["Visit the library"])

    def test_unverified_match_cannot_regenerate(self):
        service, generator = self.make_service(matches=[])
        result = service.regenerate_for_connection("A", "B", "New ideas", self.previous)
        self.assertFalse(result["success"])
        generator.generate_suggestions.assert_not_called()

    def test_invalid_feedback_rejected(self):
        service, generator = self.make_service()
        for feedback in ("", "  ", "A" * 501):
            self.assertFalse(service.regenerate_for_connection("A", "B", feedback, self.previous)["success"])
        generator.generate_suggestions.assert_not_called()

    def test_regeneration_failure_preserves_previous(self):
        service, generator = self.make_service()
        generator.generate_suggestions.return_value = {"success": False, "error": "API down"}
        result = service.regenerate_for_connection("A", "B", "New ideas", self.previous)
        self.assertFalse(result["success"])
        self.assertEqual(self.previous["outing_ideas"], ["Visit the library"])


if __name__ == "__main__":
    unittest.main()
