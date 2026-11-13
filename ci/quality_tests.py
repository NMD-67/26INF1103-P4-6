"""Regression checks for non-score fixes; run through ci/offline_tests.py."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, MagicMock, Mock, patch


class QualityChecks(unittest.TestCase):
    def test_connection_has_no_import_time_configuration_requirement(self):
        from Data_Manager.database.database_connection import DatabaseConnection
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'SUPABASE_URL'):
                DatabaseConnection().create_pool()

    def test_connection_cleanup_on_failed_start(self):
        from Data_Manager.database.database_connection import DatabaseConnection
        with patch('Data_Manager.database.database_connection.ConnectionPool') as factory:
            pool = factory.return_value
            pool.wait.side_effect = RuntimeError('Offline')
            with patch('Data_Manager.database.database_connection.logger.exception') as log:
                with self.assertRaises(RuntimeError):
                    DatabaseConnection('postgresql://invalid/offline').create_pool()
            pool.close.assert_called_once()
            log.assert_called_once()

    def test_email_timeout_and_failure_logging(self):
        from src.email_sender import EmailSender
        with patch.dict('os.environ', {'EMAIL_PASSWORD': 'synthetic-password'}):
            with patch('src.email_sender.smtplib.SMTP') as smtp:
                sender = EmailSender(timeout=12)
                self.assertEqual(sender._send('student@example.invalid', 'OTP', '1234'), 200)
                smtp.assert_called_once_with('smtp.gmail.com', 587, timeout=12)
                smtp.return_value.__enter__.return_value.send_message.assert_called_once()
                smtp.side_effect = TimeoutError('Sensitive diagnostic must not be printed')
                with patch('src.email_sender.logger.error') as log:
                    self.assertEqual(sender._send('student@example.invalid', 'OTP', '1234'), 500)
                self.assertNotIn('1234', str(log.call_args))
                self.assertNotIn('Sensitive diagnostic', str(log.call_args))

    def test_otp_uses_injected_email_sender(self):
        from services.otp_service import OTPService
        repo = Mock()
        repo.create_otp.return_value = True
        sender = NS(send=AsyncMock(return_value=200))
        service = OTPService(repo, sender)
        # AsyncMock completes immediately: no Windows event-loop sockets needed.
        with self.assertRaises(StopIteration) as completed:
            service.send_otp('1234567').send(None)
        self.assertTrue(completed.exception.value.success)
        sender.send.assert_awaited_once()
        sender.send.return_value = 500
        with self.assertRaises(StopIteration) as completed:
            service.send_otp('1234567').send(None)
        self.assertFalse(completed.exception.value.success)

    def test_failed_account_creation_returns_error(self):
        from services.user_service import UserService
        repo = Mock()
        repo.get_user.return_value = None
        repo.create.return_value = None
        self.assertFalse(UserService(repo).login_user('A').success)

    def test_repository_source_preserves_lists_and_exclusions(self):
        from AI_Manager.Profile_Matching.repository_user_source import RepositoryUserSource
        from models.user import User
        repo = Mock()
        keep = User(student_id='C', hobbies=['Coding'])
        repo.get_users_by_dealbreaker.return_value = [User(student_id='A'), User(student_id='B'), keep]
        result = RepositoryUserSource(repo).get_candidates('A', {'B'})
        self.assertEqual(result, [keep])
        self.assertEqual(result[0].hobbies, ['Coding'])
        repo.get_users_by_dealbreaker.assert_called_once_with('A')

    def test_secondary_recommendations_exclude_decided_profiles_before_ai(self):
        from AI_Manager.Profile_Matching.repository_user_source import RepositoryUserSource
        from AI_Manager.Profile_Matching.matching_service import MatchingService
        from models.user import User
        repo = Mock()
        repo.get_user.return_value = User(student_id='A')
        repo.get_users_by_dealbreaker.return_value = [User(student_id=v) for v in ('A', 'B', 'C')]
        decisions = Mock()
        decisions.get_decided_candidate_ids.return_value = NS(success=True, data=['B'])
        scorer = Mock()
        scorer.score.return_value = NS(score=80)
        service = MatchingService(scorer, RepositoryUserSource(repo), decisions)
        self.assertEqual(list(service.recommend('A')), ['C'])
        self.assertEqual(scorer.score.call_count, 1)
        self.assertEqual(scorer.score.call_args.args[1].student_id, 'C')
        decisions.get_decided_candidate_ids.return_value = NS(success=False)
        scorer.reset_mock()
        with self.assertRaises(RuntimeError):
            service.recommend('A')
        scorer.score.assert_not_called()

    def test_next_candidate_skips_stale_first_row(self):
        from services.match_service import MatchService
        from AI_Manager.Profile_Matching.repository_user_source import RepositoryUserSource
        from models.user import User
        users = Mock()
        users.get_users_by_dealbreaker.return_value = [User(student_id='C')]
        repo = Mock()
        repo.get_decided_candidate_ids.return_value = ['B']
        repo.get_candidates_for_user.return_value = [NS(student_id='B'), NS(student_id='C')]
        service = MatchService(repo, RepositoryUserSource(users))
        with patch('services.match_service.GroqKeyPool.from_env') as keys:
            result = service.get_next_candidate('A')
        self.assertTrue(result.success)
        self.assertEqual(result.data.student_id, 'C')
        keys.assert_not_called()

    def test_secondary_matching_closes_keys_on_failure(self):
        from services.match_service import MatchService
        repo, users = Mock(), Mock()
        repo.get_decided_candidate_ids.return_value = []
        repo.get_candidates_for_user.return_value = []
        users.get_candidates.return_value = [NS(student_id='B')]
        with patch('services.match_service.GroqKeyPool.from_env') as keys, \
             patch('services.match_service.MatchingService') as matching, \
             patch('services.match_service.logger.exception') as log:
            matching.return_value.recommend.side_effect = RuntimeError('Offline')
            result = MatchService(repo, users).get_next_candidate('A')
            self.assertFalse(result.success)
            keys.return_value.close.assert_called_once()
            log.assert_called_once()

    def test_missing_suggestion_keys_preserves_contacts(self):
        from AI_Manager.Suggestions_generator import SuggestionsGenerator, ConnectionSuggestionService
        from models.user import User
        from models.match import Match
        with patch.dict('os.environ', {}, clear=True), \
             patch('AI_Manager.Suggestions_generator.suggestions_generator.logger.warning'), \
             patch('AI_Manager.Suggestions_generator.suggestions_generator.Groq') as client:
            generator = SuggestionsGenerator.from_environment()
            client.assert_not_called()
        matches, users = Mock(), Mock()
        matches.get_all_matches.return_value = NS(success=True, data=[Match(student_id='B', tele_handle='@example')])
        users.get_user.return_value = NS(success=True, data=User(student_id='A'))
        result = ConnectionSuggestionService(matches, users, generator).get_matches_for_user('A')[0]
        self.assertFalse(result['success'])
        self.assertEqual(result['user_b_info']['tele_handle'], '@example')
        generator.close()

    def test_backup_only_suggestion_configuration(self):
        from AI_Manager.Suggestions_generator import SuggestionsGenerator
        with patch.dict('os.environ', {'RAPH_AI_KEY': 'synthetic-key'}, clear=True), \
             patch('AI_Manager.Suggestions_generator.suggestions_generator.Groq') as client:
            generator = SuggestionsGenerator.from_environment()
            self.assertEqual(client.call_args.kwargs['api_key'], 'synthetic-key')
            generator.close()
            client.return_value.close.assert_called_once()

    def test_real_service_honours_repository_decision_failures(self):
        from services.match_service import MatchService
        from repositories.matches_repo import MatchesRepo
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        service = MatchService(MatchesRepo(pool), user_source=Mock())
        conn.execute.return_value.fetchone.return_value = None
        self.assertFalse(service.handle_candidate_decision('A', 'B', True).success)
        conn.execute.return_value.fetchone.return_value = {'status': 'rejected'}
        self.assertTrue(service.handle_candidate_decision('A', 'B', False).success)
        self.assertEqual(conn.execute.call_args.args[1], ('rejected', 'A', 'B'))

    def test_real_service_honours_repository_delete_failures(self):
        from services.user_service import UserService
        from repositories.user_repo import UserRepo
        pool = MagicMock()
        conn = pool.connection.return_value.__enter__.return_value
        service = UserService(UserRepo(pool))
        conn.execute.return_value.fetchone.return_value = None
        self.assertFalse(service.delete_user('A').success)
        conn.execute.return_value.fetchone.return_value = {'student_id': 'A'}
        self.assertTrue(service.delete_user('A').success)
        self.assertEqual(conn.execute.call_args.args[1], ('A',))

    def test_all_scoring_keys_exhausted_is_controlled(self):
        import groq
        import httpx
        from models.user import User
        from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
        from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
        with patch('AI_Manager.Profile_Matching.groq_key_pool.Groq'):
            pool = GroqKeyPool(['synthetic-one', 'synthetic-two'])
        error = groq.AuthenticationError('Synthetic', body={}, response=httpx.Response(
            401, request=httpx.Request('POST', 'https://example.invalid')))
        scorer = GroqScorer(pool)
        with patch.object(scorer, '_call_api', side_effect=error) as call, \
             patch('AI_Manager.Profile_Matching.groq_key_pool.logger'), \
             patch('AI_Manager.Profile_Matching.groq_scorer.logger'):
            self.assertIsNone(scorer.score(User(student_id='A'), User(student_id='B')))
            self.assertEqual(call.call_count, 2)
        pool.close()
