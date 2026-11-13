"""Offline regression tests. Run from any folder: python ci/offline_tests.py."""
import ast
from contextlib import ExitStack, redirect_stdout
from datetime import date
from importlib import import_module
from io import StringIO
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace as NS
from unittest.mock import MagicMock, Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class OfflineChecks(unittest.TestCase):
    def test_application_syntax(self):
        excluded = {"tele", "tests", "Unused", "__pycache__", ".venv", "venv", ".git"}
        files = [p for p in ROOT.rglob("*.py")
                 if not (set(p.relative_to(ROOT).parts) & excluded)
                 and not p.name.startswith(("test", "automated_test"))]
        self.assertTrue(files)
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))

    def test_birthday_and_age(self):
        from Logic_Manager.profile_logic_manager import ProfileLogicManager
        logic = ProfileLogicManager()
        self.assertEqual(logic.parse_birthday("29/02/2024"), date(2024, 2, 29))
        with self.assertRaises(ValueError):
            logic.parse_birthday("29/02/2023")
        self.assertEqual(logic.calculate_age(date(2004, 6, 15), date(2026, 6, 14)), 21)
        self.assertEqual(logic.calculate_age(date(2004, 6, 15), date(2026, 6, 15)), 22)
        self.assertIsNone(logic.validate_age_preferences({"min_preferred_age": 18, "max_preferred_age": 30}))
        self.assertIsNotNone(logic.validate_age_preferences({"min_preferred_age": 25, "max_preferred_age": 20}))

    def test_blacklist_input_and_display(self):
        from config.user_fields import PROFILE_FIELDS
        from IO_Manager.profile_validator import ProfileValidator
        from IO_Manager.console_io import ConsoleIO
        fields = {f["key"]: f for f in PROFILE_FIELDS}
        validator = ProfileValidator()
        self.assertEqual(validator.validate_field("2,3,2", fields["race_preference"]), (["Chinese", "Malay"], None))
        self.assertEqual(validator.validate_field("", fields["race_preference"]), ([], None))
        self.assertIsNotNone(validator.validate_field("1,2", fields["race_preference"])[1])
        output = []
        ConsoleIO(write=output.append).show_profile({"race": "Indian", "race_preference": ["Chinese"]})
        self.assertIn("  Race: Indian", output)
        self.assertIn("  Race Blacklist: Chinese", output)
        self.assertIn("\n=== Matching Preferences ===", output)
        self.assertNotIn("dealbreakers", fields)

    def test_blacklist_and_age_filtering(self):
        from repositories.user_repo import UserRepo
        from models.user import User
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        repo = UserRepo(pool)
        repo.get_all_users = Mock(return_value=[
            User(student_id="A", gender="Male", age=22, race="Indian", religion="Islam", match_preference="Both"),
            User(student_id="B", gender="Male", age=22, race="Chinese", religion="Islam", match_preference="Both"),
            User(student_id="C", gender="Male", age=22, race="Indian", religion="Buddhism", match_preference="Both"),
            User(student_id="D", gender="Male", age=22, race="Indian", religion="Islam", match_preference="Both"),
            User(student_id="E", gender="Male", age=26, race="Indian", religion="Islam", match_preference="Both")])
        prefs = {"student_id": "A", "min_age": 20, "max_age": 25,
                 "gender": "Male", "race": ["Chinese"], "religion": ["Buddhism"]}
        conn.execute.return_value.fetchall.return_value = [prefs]
        self.assertEqual([u.student_id for u in repo.get_users_by_dealbreaker("A")], ["D"])
        # D excludes A's race, so A must not see D either.
        conn.execute.return_value.fetchall.return_value = [prefs, {"student_id": "D", "race": ["Indian"]}]
        self.assertEqual(repo.get_users_by_dealbreaker("A"), [])
        conn.execute.return_value.fetchall.return_value = []
        self.assertEqual(len(repo.get_users_by_dealbreaker("A")), 4)

    def test_otp_is_private_and_consumed(self):
        from services.otp_service import OTPService
        repo = Mock()
        repo.get_otp.return_value = 1234
        output = StringIO()
        with redirect_stdout(output):
            result = OTPService(repo).verify_otp("A", "0000", Mock())
        self.assertFalse(result.success)
        self.assertEqual(output.getvalue(), "")
        repo.delete_otp.assert_not_called()
        repo.delete_otp.return_value = True
        users = Mock()
        users.login_user.return_value = NS(success=True)
        self.assertTrue(OTPService(repo).verify_otp("A", "1234", users).success)
        repo.delete_otp.assert_called_once_with("A", expected_otp=1234)
        repo.delete_otp.return_value = False
        self.assertFalse(OTPService(repo).verify_otp("A", "1234", users).success)

    def test_ai_schema_and_polymorphism(self):
        from models.user import User
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        from AI_Manager.Profile_Matching.fake_scorer import FakeScorer
        raw = '{"score":80,"reason":"Shared hobby"}'
        client = Mock()
        client.chat.completions.create.return_value = NS(choices=[NS(
            finish_reason="stop", message=NS(content=raw))])
        for scorer in (GroqScorer(NS(client=client)), FakeScorer(80)):
            self.assertEqual(scorer.score(User(student_id="A"), User(student_id="B")).score, 80)
        for raw in ('invalid', '[]', '{"score":true}', '{"score":101}', '{"score":-1}', '{"score":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                GroqScorer._parse_and_validate(raw)

    def test_invalid_key_falls_back(self):
        import groq
        import httpx
        from models.user import User
        from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        for error_type, code in ((groq.AuthenticationError, 401), (groq.RateLimitError, 429)):
            with patch("AI_Manager.Profile_Matching.groq_key_pool.Groq"):
                pool = GroqKeyPool(["synthetic-one", "synthetic-two"])
            error = error_type("Synthetic failure", body={}, response=httpx.Response(
                code, request=httpx.Request("POST", "https://example.invalid")))
            scorer = GroqScorer(pool)
            with patch.object(scorer, "_call_api", side_effect=[error, '{"score":80,"reason":"Shared hobby"}']) as call:
                result = scorer.score(User(student_id="A"), User(student_id="B"))
            self.assertEqual(result.score, 80)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(pool._index, 1)

    def test_suggestions_schema(self):
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        generator = SuggestionsGenerator(Mock(), sleep=lambda seconds: None)
        valid = '{"common_interests":["Coding"],"conversation_starters":["What do you build?"],"outing_ideas":["Campus event"]}'
        self.assertEqual(generator._validate_response(valid)["common_interests"], ["Coding"])
        for raw in ('invalid', '{}', '{"common_interests":[]}'):
            with self.assertRaises(ValueError):
                generator._validate_response(raw)

    def test_matching_excludes_old_and_decided_profiles(self):
        from sitogether_app import SITogetherApp
        from AI_Manager.Profile_Matching.score_result import ScoreResult
        app = SITogetherApp.__new__(SITogetherApp)
        app._student_id = "A"
        app._io = Mock()
        app._io.ask_match_decision.return_value = "0"
        app._users = Mock()
        app._users.filter_users_by_dealbreaker.return_value = NS(success=True,
            data=[NS(student_id=s) for s in ("A", "B", "C", "D")])
        app._matches = Mock()
        app._matches.get_decided_candidate_ids.return_value = NS(success=True, data=["B", "C"])
        app._matches.create_match.return_value = NS(success=True)
        app._matches.get_candidates_for_user.return_value = NS(success=True,
            data=[NS(student_id=s) for s in ("OLD", "B", "D")])
        app._load_profile = Mock(return_value=NS(student_id="A"))
        app._scoring = Mock()
        app._scoring.score.return_value = ScoreResult(80, "Shared hobby")
        app.view_matches()
        self.assertEqual([c.args[1].student_id for c in app._scoring.score.call_args_list], ["D"])
        self.assertEqual([c.args[0].student_id for c in app._io.show_candidate.call_args_list], ["D"])

    def test_save_retry_retains_answers(self):
        from sitogether_app import SITogetherApp
        app = SITogetherApp.__new__(SITogetherApp)
        app._io = Mock()
        app._io.confirm.return_value = True
        answers = {"name": "Example"}
        app._save_profile = Mock(side_effect=[RuntimeError("Offline"), False, True])
        with patch("sitogether_app.logger.exception") as log:
            self.assertTrue(app._save_profile_with_retry(answers))
            log.assert_called_once()
        self.assertTrue(all(c.args[0] is answers for c in app._save_profile.call_args_list))
        app._save_profile = Mock(return_value=False)
        app._io.confirm.return_value = False
        self.assertFalse(app._save_profile_with_retry(answers))

    def test_repository_update_checks_user_exists(self):
        from repositories.user_repo import UserRepo
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = None
        self.assertFalse(UserRepo(pool).update("missing", {"hobbies": []}))
        self.assertEqual(conn.execute.call_count, 1)
        conn.execute.reset_mock()
        conn.execute.return_value.fetchone.return_value = {"student_id": "A"}
        self.assertTrue(UserRepo(pool).update("A", {"hobbies": []}))
        self.assertEqual(conn.execute.call_count, 3)
        self.assertFalse(UserRepo(pool).update("A", {"unknown": "value"}))

    def test_connection_survives_suggestion_failure(self):
        from models.user import User
        from models.match import Match
        from AI_Manager.Suggestions_generator import ConnectionSuggestionService
        from IO_Manager.console_io import ConsoleIO
        matches = Mock()
        matches.get_all_matches.return_value = NS(success=True, data=[
            Match(student_id="B", name="Example", tele_handle="@example")])
        users = Mock()
        users.get_user.return_value = NS(success=True, data=User(student_id="A"))
        generator = Mock()
        service = ConnectionSuggestionService(matches, users, generator)
        for failure in (False, True):
            generator.generate_suggestions.return_value = {"success": False, "error": "Offline"}
            generator.generate_suggestions.side_effect = RuntimeError("Offline") if failure else None
            with patch("AI_Manager.Suggestions_generator.connection_suggestion_service.logger.exception"):
                result = service.get_matches_for_user("A")[0]
            text = ConsoleIO().format_recommendations(result)
            self.assertIn("@example", text)
            self.assertIn("temporarily unavailable", text)
        matches.get_all_matches.return_value = NS(success=False)
        with patch("AI_Manager.Suggestions_generator.connection_suggestion_service.logger.warning"):
            result = service.get_matches_for_user("A")[0]
        self.assertNotIn("@example", ConsoleIO().format_recommendations(result))

    def test_startup_wiring(self):
        import main
        from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        with patch.dict("os.environ", {"SUPABASE_URL": "postgresql://invalid/unused"}):
            connection = import_module("Data_Manager.database.connection")
        with ExitStack() as mocks:
            pool = mocks.enter_context(patch.object(connection, "create_connection_pool"))
            keys = mocks.enter_context(patch.object(GroqKeyPool, "from_env"))
            mocks.enter_context(patch.object(SuggestionsGenerator, "from_environment"))
            run = mocks.enter_context(patch.object(main.SITogetherApp, "run"))
            main.main()
            run.assert_called_once()
            pool.return_value.close.assert_called_once()
            keys.return_value.close.assert_called_once()


if __name__ == "__main__":
    # Block real credentials, networking and interactive input during tests.
    with ExitStack() as guards:
        guards.enter_context(patch.dict("os.environ", {}, clear=True))
        guards.enter_context(patch("dotenv.load_dotenv", return_value=False))
        guards.enter_context(patch("socket.socket.connect", side_effect=RuntimeError("Network disabled in CI tests")))
        guards.enter_context(patch("socket.socket.connect_ex", side_effect=RuntimeError("Network disabled in CI tests")))
        guards.enter_context(patch("builtins.input", side_effect=RuntimeError("Interactive input disabled in CI tests")))
        unittest.main(verbosity=2)
