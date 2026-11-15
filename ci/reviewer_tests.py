"""Offline checks for hybrid score review and both recommendation entry paths."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch
from models.user import User
from models.category_scores import CategoryScores
from AI_Manager.Profile_Matching.score_result import ScoreResult
from AI_Manager.Profile_Matching.AI_Validator_Workflow.review_service import ReviewService
from Logic_Manager.Matching.scoring_pipeline import ScoringPipeline


class ReviewerChecks(unittest.TestCase):
    def setUp(self):
        self.viewer = User(student_id="A")
        self.candidates = [User(student_id="B")]
        self.original = [CategoryScores(80, 80, 80)]

    def validator(self, checks):
        return NS(category="interests_lifestyle", validate_batch=lambda *args: checks)

    def test_correction_none_and_dry_run(self):
        reviewer = ReviewService([self.validator([20])])
        self.assertEqual(reviewer.correct(self.viewer, self.candidates, self.original)[0].interests_lifestyle, 45)
        for reviewer in (ReviewService([self.validator([None])]),
                         ReviewService([self.validator([20])], dry_run=True)):
            self.assertEqual(reviewer.correct(self.viewer, self.candidates, self.original), self.original)

    def test_malformed_validator_preserves_scores(self):
        for values in ([250], [-1], [True], [float("nan")], [float("inf")], ["bad"], [], [50, 50]):
            with self.subTest(values=values), self.assertLogs(level="ERROR"):
                actual = ReviewService([self.validator(values)]).correct(self.viewer, self.candidates, self.original)
                self.assertEqual(actual, self.original)

    def test_invalid_category_and_validator_exception(self):
        validator = self.validator([20])
        validator.category = "unknown"
        broken = Mock(category="interests_lifestyle")
        broken.validate_batch.side_effect = RuntimeError("failed")
        for value in (validator, broken):
            with self.assertLogs(level="ERROR"):
                self.assertEqual(ReviewService([value]).correct(self.viewer, self.candidates, self.original), self.original)

    def test_invalid_tolerance(self):
        for value in (-1, True, "25", float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                ReviewService([], tolerance=value)

    def test_pipeline_checks_reviewer_contract(self):
        scorer = Mock()
        scorer.score.return_value = ScoreResult(self.original[0], "Reason")
        reviewer = Mock()
        for output in ([], self.original * 2, [CategoryScores(200, 80, 80)], ["bad"]):
            reviewer.correct.return_value = output
            with self.assertLogs(level="ERROR"):
                result = ScoringPipeline(scorer, Mock(), reviewer=reviewer).score_candidates(self.viewer, self.candidates)
            self.assertEqual(result["B"].categories, self.original[0])
        reviewer.correct.side_effect = RuntimeError("failed")
        with self.assertLogs(level="ERROR"):
            self.assertEqual(ScoringPipeline(scorer, Mock(), reviewer=reviewer).score_candidates(self.viewer, self.candidates)["B"].overall, 80)

    def test_corrected_scores_saved_by_shared_app_service(self):
        from Logic_Manager.services.recommendation_service import RecommendationService
        users, matches, scorer = Mock(), Mock(), Mock()
        users.filter_users_by_dealbreaker.return_value = NS(success=True, data=self.candidates)
        users.get_profile.return_value = NS(success=True, data=self.viewer)
        matches.get_decided_candidate_ids.return_value = NS(success=True, data=[])
        matches.create_match.return_value = NS(success=True)
        matches.get_candidates_for_user.return_value = NS(success=True, data=self.candidates)
        scorer.score.return_value = ScoreResult(self.original[0], "Reason")
        reviewer = ReviewService([self.validator([20])])
        with patch("Logic_Manager.services.recommendation_service.create_reviewer", return_value=reviewer) as factory:
            service = RecommendationService(users, matches, scorer)
            self.assertTrue(service.get_recommendations("A").success)
            self.assertTrue(service.get_recommendations("A").success)
            factory.assert_called_once()
        matches.create_match.assert_called_with(student_id="A", candidate_id="B",
            compatibility_score=66, interest_score=45, personality_score=80,
            preferences_score=80, reason="Reason")

    def test_secondary_path_retains_batch_limit_and_review(self):
        from Logic_Manager.Matching.matching_service import MatchingService
        users, matches, scorer = Mock(), Mock(), Mock()
        users.get_user.return_value = self.viewer
        users.get_candidates.return_value = [User(student_id=str(i)) for i in range(8)]
        matches.get_decided_candidate_ids.return_value = NS(success=True, data=[])
        matches.create_match.return_value = NS(success=True)
        scorer.score.return_value = ScoreResult(self.original[0])
        reviewer = ReviewService([self.validator([20]*5)])
        service = MatchingService(scorer, users, matches, reviewer=reviewer)
        results = service.recommend("A", limit=5)
        self.assertEqual(len(results), 5)
        self.assertEqual(scorer.score.call_count, 5)
        self.assertTrue(all(value.overall == 66 for value in results.values()))
        self.assertEqual(service.save("A", results)["saved"], 5)

    def test_missing_model_keeps_other_validators(self):
        from AI_Manager.Profile_Matching.AI_Validator_Workflow.reviewer_factory import create_reviewer
        with patch("AI_Manager.Profile_Matching.AI_Validator_Workflow.reviewer_factory.SentenceSimilarity.from_env", side_effect=RuntimeError("not installed")), self.assertLogs(level="WARNING"):
            reviewer = create_reviewer()
        self.assertEqual(len(reviewer._validators), 2)
        self.assertEqual(reviewer.correct(self.viewer, self.candidates, self.original), self.original)

    def test_ranking_uses_corrected_scores(self):
        scorer = Mock()
        scorer.score.side_effect = [ScoreResult(CategoryScores(90, 80, 80)),
                                   ScoreResult(CategoryScores(70, 80, 80))]
        reviewer = ReviewService([self.validator([0, 100])])
        pipeline = ScoringPipeline(scorer, Mock(), reviewer=reviewer)
        result = pipeline.score_candidates(self.viewer, [User(student_id="B"), User(student_id="C")])
        self.assertEqual(list(result), ["C", "B"])
        self.assertEqual(result["B"].categories.interests_lifestyle, 25)
        self.assertEqual(result["C"].categories.interests_lifestyle, 75)

    def test_factory_uses_all_three_validators_when_model_available(self):
        from AI_Manager.Profile_Matching.AI_Validator_Workflow.reviewer_factory import create_reviewer
        with patch("AI_Manager.Profile_Matching.AI_Validator_Workflow.reviewer_factory.SentenceSimilarity.from_env", return_value=Mock()):
            reviewer = create_reviewer()
        self.assertEqual({v.category for v in reviewer._validators},
                         {"interests_lifestyle", "personality_values", "relationship_goals"})
