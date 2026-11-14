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
from models.category_scores import CategoryScores
from AI_Manager.Profile_Matching.score_result import ScoreResult


class OfflineChecks(unittest.TestCase):
    def test_application_syntax(self):
        excluded = {"tests", "Unused", "__pycache__", ".venv", "venv", ".git"}
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
        from Data_Manager.repositories.user_repo import UserRepo
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
        from Logic_Manager.services.otp_service import OTPService
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
        raw = '{"interests_lifestyle":80,"personality_values":80,"relationship_goals":80,"reason":"Shared hobby"}'
        client = Mock()
        client.chat.completions.create.return_value = NS(choices=[NS(
            finish_reason="stop", message=NS(content=raw))])
        for scorer in (GroqScorer(NS(client=client)), FakeScorer(80)):
            self.assertEqual(scorer.score(User(student_id="A"), User(student_id="B")).categories.interests_lifestyle, 80)
        for raw in ('invalid', '[]', '{"score":true}', '{"score":101}', '{"score":-1}', '{"score":NaN}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                GroqScorer._parse_and_validate(raw)

    def test_scoring_requires_reason(self):
        import json
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        for payload in ({"interests_lifestyle": 80, "personality_values": 80, "relationship_goals": 80}, *(
            {"interests_lifestyle": 80, "personality_values": 80, "relationship_goals": 80, "reason": value}
            for value in (None, "", "   ", 123, [], {})
        )):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                GroqScorer._parse_and_validate(json.dumps(payload))
        result = GroqScorer._parse_and_validate(
            '{"interests_lifestyle":80,"personality_values":80,"relationship_goals":80,"reason":"Shared hobby"}')
        self.assertEqual(result.reason, "Shared hobby")

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
            with patch.object(scorer, "_call_api", side_effect=[error, '{"interests_lifestyle":80,"personality_values":80,"relationship_goals":80,"reason":"Shared hobby"}']) as call:
                result = scorer.score(User(student_id="A"), User(student_id="B"))
            self.assertEqual(result.categories.interests_lifestyle, 80)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(pool._index, 1)

    def test_each_ai_category_is_validated(self):
        import json
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        valid = dict(interests_lifestyle=90, personality_values=60,
                     relationship_goals=30, reason="Shared interests")
        for key in ("interests_lifestyle", "personality_values", "relationship_goals"):
            for invalid in (True, -1, 101, "80", None, float("nan")):
                with self.subTest(key=key, value=invalid), self.assertRaises(ValueError):
                    GroqScorer._parse_and_validate(json.dumps({**valid, key: invalid}))

    def test_shared_recommendations_save_weighted_category_scores(self):
        from Logic_Manager.services.recommendation_service import RecommendationService
        users, matches, scoring = Mock(), Mock(), Mock()
        users.filter_users_by_dealbreaker.return_value = NS(success=True, data=[NS(student_id="B")])
        users.get_profile.return_value = NS(success=True, data=NS(student_id="A"))
        matches.get_decided_candidate_ids.return_value = NS(success=True, data=[])
        matches.create_match.return_value = NS(success=True)
        matches.get_candidates_for_user.return_value = NS(success=True, data=[NS(student_id="B")])
        scoring.score.return_value = ScoreResult(CategoryScores(90, 60, 30), "Shared interests")
        result = RecommendationService(users, matches, scoring).get_recommendations("A")
        self.assertTrue(result.success)
        matches.create_match.assert_called_once_with(
            student_id="A", candidate_id="B", compatibility_score=63,
            interest_score=90, personality_score=60, preferences_score=30,
            reason="Shared interests")

    def test_category_scores_round_trip_and_upsert(self):
        from models.candidate import Candidate
        from Data_Manager.repositories.matches_repo import MatchesRepo
        from Logic_Manager.services.match_service import MatchService
        candidate = Candidate.from_dict(dict(student_id="B", compatibility_score=63,
            interest_score=90, personality_score=60, preferences_score=30))
        self.assertEqual(candidate.interest_score, 90)
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        conn.execute.return_value.fetchone.return_value = {"student_id": "A"}
        service = MatchService(MatchesRepo(pool), user_source=Mock())
        self.assertTrue(service.create_match("A", "B", 63, 90, 60, 30, "Reason").success)
        query, values = conn.execute.call_args.args
        self.assertEqual(values, ("A", "B", 63, "Reason", 90, 60, 30))
        update = query.split("DO UPDATE SET")[1].split("RETURNING")[0]
        for field in ("interest_score", "personality_score", "preferences_score"):
            self.assertIn(f"{field} = EXCLUDED.{field}", update)
        self.assertNotIn("status =", update)

    def test_scores_display_for_candidates_and_failed_connection_suggestions(self):
        from IO_Manager.console_io import ConsoleIO
        from IO_Manager.telegram.telegram_io import TelegramIO
        from models.candidate import Candidate
        from models.match import Match
        from models.user import User
        from Logic_Manager.services.connection_suggestion_service import ConnectionSuggestionService
        scores = dict(compatibility_score=63, interest_score=90,
                      personality_score=60, preferences_score=30, reason="Shared interests")
        candidate = Candidate(student_id="B", **scores)
        expected = ConsoleIO.format_compatibility(scores)
        lines = []
        ConsoleIO(write=lines.append).show_candidate(candidate)
        self.assertIn(expected, "\n".join(lines))
        self.assertIn(expected, TelegramIO.candidate(candidate))
        matches, users, generator = Mock(), Mock(), Mock()
        matches.get_all_matches.return_value = NS(success=True,
            data=[Match(student_id="B", tele_handle="@example", **scores)])
        users.get_user.return_value = NS(success=True, data=User(student_id="A"))
        generator.generate_suggestions.return_value = {"success": False}
        result = ConnectionSuggestionService(matches, users, generator).get_matches_for_user("A")[0]
        self.assertEqual(result["compatibility"], scores)
        self.assertIn(expected, ConsoleIO().format_recommendations(result))
        self.assertIn(expected, TelegramIO.connection(result))
        self.assertIn("@example", TelegramIO.connection(result))
        users.get_user.return_value = NS(success=False)
        failed = ConnectionSuggestionService(matches, users, generator).get_matches_for_user("A")[0]
        self.assertEqual(failed["compatibility"], scores)
        self.assertIn("Overall Compatibility: 0%", ConsoleIO.format_compatibility({"compatibility_score": 0}))
        self.assertIn("Overall Compatibility: Not available", ConsoleIO.format_compatibility({}))

    def test_connection_repository_loads_viewer_scores(self):
        from Data_Manager.repositories.matches_repo import MatchesRepo
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        conn.execute.return_value.fetchall.side_effect = [
            [dict(student_id="B", compatibility_score=63, interest_score=90,
                  personality_score=60, preferences_score=30, reason="Reason")],
            [], [], [], []]
        records = MatchesRepo(pool).get_matches_for_user("A")
        self.assertEqual(records[0].interest_score, 90)
        self.assertEqual(records[0].compatibility_score, 63)
        query = conn.execute.call_args_list[0].args[0]
        for field in ("compatibility_score", "interest_score", "personality_score", "preferences_score", "reason"):
            self.assertIn("m." + field, query)

    def test_multicondition_classification_boundaries(self):
        from Logic_Manager.Matching.compatibility_classifier import CompatibilityClassifier
        rule = CompatibilityClassifier()
        def classify(a, b, c):
            return rule.classify(dict(interest_score=a, personality_score=b, preferences_score=c))
        for value, expected in ((0, "Low compatibility"), (49, "Low compatibility"),
                                (50, "Moderate compatibility"), (69, "Moderate compatibility"),
                                (70, "Strong compatibility"), (100, "Strong compatibility")):
            self.assertEqual(classify(value, value, value), expected)
        # Each field independently changes the outcome even when the other two are high.
        for values in ((69, 100, 100), (100, 69, 100), (100, 100, 69)):
            self.assertEqual(classify(*values), "Moderate compatibility")
        for values in ((49, 100, 100), (100, 49, 100), (100, 100, 49)):
            self.assertEqual(classify(*values), "Low compatibility")

    def test_multicondition_missing_and_invalid_scores(self):
        from Logic_Manager.Matching.compatibility_classifier import CompatibilityClassifier
        rule = CompatibilityClassifier()
        self.assertEqual(rule.classify({}), "Not available")
        for key in ("interest_score", "personality_score", "preferences_score"):
            for value in (None, True, "80", -1, 101, float("nan"), float("inf")):
                scores = dict(interest_score=80, personality_score=80, preferences_score=80)
                scores[key] = value
                self.assertEqual(rule.classify(scores), "Not available")

    def test_multicondition_rule_uses_parsed_ai_and_appears_in_both_interfaces(self):
        import json
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        from Logic_Manager.Matching.score_calculator import ScoreCalculator
        from models.candidate import Candidate
        from IO_Manager.console_io import ConsoleIO
        from IO_Manager.telegram.telegram_io import TelegramIO
        parsed = GroqScorer._parse_and_validate(json.dumps(dict(
            interests_lifestyle=100, personality_values=100,
            relationship_goals=40, reason="Different goals")))
        c = parsed.categories
        scores = dict(compatibility_score=ScoreCalculator().overall(c),
            interest_score=c.interests_lifestyle, personality_score=c.personality_values,
            preferences_score=c.relationship_goals, reason=parsed.reason)
        self.assertEqual(scores["compatibility_score"], 82)
        candidate = Candidate(student_id="B", **scores)
        lines = []
        ConsoleIO(write=lines.append).show_candidate(candidate)
        self.assertIn("Match category: Low compatibility", "\n".join(lines))
        self.assertIn("Match category: Low compatibility", TelegramIO.candidate(candidate))
        connection = dict(success=False, user_b_info={"name": "Example"}, compatibility=scores)
        self.assertIn("Match category: Low compatibility", ConsoleIO().format_recommendations(connection))
        self.assertIn("Match category: Low compatibility", TelegramIO.connection(connection))

    def test_shared_pipeline_sorts_scores_and_reports_save_failures(self):
        from Logic_Manager.Matching.scoring_pipeline import ScoringPipeline
        scorer, matches = Mock(), Mock()
        scorer.score.side_effect = [ScoreResult(CategoryScores(50, 50, 50), "One"),
                                   None, ScoreResult(CategoryScores(90, 60, 30), "Two")]
        pipeline = ScoringPipeline(scorer, matches)
        results = pipeline.score_candidates(NS(student_id="A"),
            [NS(student_id=s) for s in ("B", "C", "D")])
        self.assertEqual(list(results), ["D", "B"])
        self.assertEqual(results["D"].overall, 63)
        matches.create_match.side_effect = [RuntimeError("Offline"), NS(success=False)]
        with patch("Logic_Manager.Matching.scoring_pipeline.logger.exception") as log:
            counts = pipeline.save_results("A", results)
        self.assertEqual(counts, dict(saved=0, not_saved=1, failed=1))
        log.assert_called_once()

    def test_recommendations_report_ai_and_save_failures(self):
        from Logic_Manager.services.recommendation_service import RecommendationService
        users, matches, scorer = Mock(), Mock(), Mock()
        users.filter_users_by_dealbreaker.return_value = NS(success=True, data=[NS(student_id="B")])
        users.get_profile.return_value = NS(success=True, data=NS(student_id="A"))
        matches.get_decided_candidate_ids.return_value = NS(success=True, data=[])
        service = RecommendationService(users, matches, scorer)
        scorer.score.return_value = None
        result = service.get_recommendations("A")
        self.assertFalse(result.success)
        self.assertIn("AI could not score", result.error_msg)
        matches.create_match.assert_not_called()
        matches.get_candidates_for_user.assert_not_called()
        scorer.score.return_value = ScoreResult(CategoryScores(80, 80, 80), "Reason")
        matches.create_match.return_value = NS(success=False)
        self.assertFalse(service.get_recommendations("A").success)
        matches.get_candidates_for_user.assert_not_called()

    def test_empty_query_results_are_not_database_failures(self):
        from Logic_Manager.services.user_service import UserService
        from Logic_Manager.services.match_service import MatchService
        repo = Mock()
        repo.get_users_by_dealbreaker.return_value = []
        repo.get_candidates_for_user.return_value = []
        self.assertEqual(UserService(repo).filter_users_by_dealbreaker("A").data, [])
        self.assertEqual(MatchService(repo, user_source=Mock()).get_candidates_for_user("A").data, [])

    def test_inherited_model_details_include_specialised_fields(self):
        from models.candidate import Candidate
        from models.profile import Profile
        from models.match import Match
        from models.dealbreaker import DealBreaker
        candidate = Candidate(student_id="A", compatibility_score=80, interest_score=90, reason="Reason")
        self.assertEqual(candidate.get_user_details()["interest_score"], 90)
        self.assertEqual(candidate.get_user_details()["reason"], "Reason")
        preferences = DealBreaker(min_age=20)
        self.assertIs(Profile(student_id="A", dealbreakers=preferences).get_user_details()["dealbreakers"], preferences)
        self.assertEqual(Match(student_id="A", preferences_score=70).get_user_details()["preferences_score"], 70)

    def test_birthday_is_input_only_in_repository_mapping(self):
        from config.user_fields import SCALAR_FIELDS, REPOSITORY_FIELD_CONFIG, PROFILE_FIELDS
        self.assertNotIn("birthday", SCALAR_FIELDS)
        self.assertNotIn("birthday", REPOSITORY_FIELD_CONFIG)
        self.assertIn("birthday", [f["key"] for f in PROFILE_FIELDS])

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
        app._scoring.score.return_value = ScoreResult(CategoryScores(80, 80, 80), "Shared hobby")
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
        from Data_Manager.repositories.user_repo import UserRepo
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
        from Logic_Manager.services.connection_suggestion_service import ConnectionSuggestionService
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
            with patch("Logic_Manager.services.connection_suggestion_service.logger.exception"):
                result = service.get_matches_for_user("A")[0]
            text = ConsoleIO().format_recommendations(result)
            self.assertIn("@example", text)
            self.assertIn("temporarily unavailable", text)
        matches.get_all_matches.return_value = NS(success=False)
        with patch("Logic_Manager.services.connection_suggestion_service.logger.warning"):
            result = service.get_matches_for_user("A")[0]
        self.assertNotIn("@example", ConsoleIO().format_recommendations(result))

    def test_suggestion_clients_close(self):
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        primary, backup = Mock(), Mock()
        generator = SuggestionsGenerator(primary, backup)
        generator.close()
        primary.close.assert_called_once()
        backup.close.assert_called_once()
        primary.reset_mock()
        backup.reset_mock()
        primary.close.side_effect = RuntimeError("Close failed")
        with patch("AI_Manager.Suggestions_generator.suggestions_generator.logger.exception") as log:
            generator.close()
        log.assert_called_once()
        backup.close.assert_called_once()
        SuggestionsGenerator(Mock()).close()

    def test_startup_wiring(self):
        import main
        from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        with patch.dict("os.environ", {"SUPABASE_URL": "postgresql://invalid/unused"}):
            connection = import_module("Data_Manager.database.database_connection")
        with ExitStack() as mocks:
            pool = mocks.enter_context(patch.object(connection.DatabaseConnection, "create_pool"))
            keys = mocks.enter_context(patch.object(GroqKeyPool, "from_env"))
            suggestions = mocks.enter_context(patch.object(SuggestionsGenerator, "from_environment"))
            run = mocks.enter_context(patch.object(main.SITogetherApp, "run"))
            for failure in (False, True):
                run.reset_mock()
                pool.return_value.close.reset_mock()
                keys.return_value.close.reset_mock()
                suggestions.return_value.close.reset_mock()
                run.side_effect = RuntimeError("Session failed") if failure else None
                if failure:
                    with self.assertRaises(RuntimeError):
                        main.main()
                else:
                    main.main()
                run.assert_called_once()
                pool.return_value.close.assert_called_once()
                keys.assert_not_called()
                keys.return_value.close.assert_not_called()
                suggestions.return_value.close.assert_called_once()


def load_tests(loader, tests, pattern):
    # Only maintained offline checks; never discover scripts that call live services.
    from ci.quality_tests import QualityChecks
    tests.addTests(loader.loadTestsFromTestCase(QualityChecks))
    from ci.telegram_tests import TelegramChecks
    tests.addTests(loader.loadTestsFromTestCase(TelegramChecks))
    tests.addTests(loader.discover(str(ROOT / "tests"), pattern="test_mutual_preference_filter.py"))
    tests.addTests(loader.discover(str(ROOT / "tests"), pattern="test_birthday_privacy.py"))
    return tests


if __name__ == "__main__":
    # Block real credentials, networking and interactive input during tests.
    with ExitStack() as guards:
        guards.enter_context(patch.dict("os.environ", {}, clear=True))
        guards.enter_context(patch("dotenv.load_dotenv", return_value=False))
        guards.enter_context(patch("socket.socket.connect", side_effect=RuntimeError("Network disabled in CI tests")))
        guards.enter_context(patch("socket.socket.connect_ex", side_effect=RuntimeError("Network disabled in CI tests")))
        guards.enter_context(patch("builtins.input", side_effect=RuntimeError("Interactive input disabled in CI tests")))
        unittest.main(verbosity=2)
