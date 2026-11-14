"""Telegram adapter regressions with fake messages and external services."""
import importlib
import unittest
from types import SimpleNamespace as NS
from unittest.mock import AsyncMock, Mock, patch
from results.success import Success
from results.error import Error
from models.profile import Profile
from models.candidate import Candidate
from models.dealbreaker import DealBreaker
from config.user_fields import PROFILE_FIELDS
from IO_Manager.telegram.telegram_app import TelegramApp
from IO_Manager.telegram.profile_setup import STATE_KEY


async def immediate_thread(function, *args, **kwargs):
    """Run fakes synchronously; no Windows event-loop sockets needed in CI."""
    return function(*args, **kwargs)


class TelegramChecks(unittest.TestCase):
    def setUp(self):
        self.thread = patch('asyncio.to_thread', new=immediate_thread)
        self.thread.start()
        self.addCleanup(self.thread.stop)
        self.users, self.otp, self.bots, self.matches, self.scoring, self.suggestions = [Mock() for _ in range(6)]
        self.profile = Profile(student_id='1234567', name='Clint', age=21, horoscope='Gemini',
            gender='Male', year=2, course='Applied Artificial Intelligence', here_for='Both',
            match_preference='Both', tele_handle='@example', hobbies=['Coding'],
            expectations='Enjoy time together', dealbreakers=DealBreaker())
        self.users.get_profile.return_value = Success(self.profile)
        self.users.update_user.return_value = Success('saved')
        self.bots.get_student_id.return_value = Success('1234567')
        self.bots.logout.return_value = Success('logged out')
        self.bots.add_bot.return_value = Success('linked')
        self.controller = TelegramApp(self.users, self.otp, self.bots, self.matches, self.scoring, self.suggestions)
        self.message = NS(text='', reply_text=AsyncMock())
        self.query = NS(data='', answer=AsyncMock(), edit_message_reply_markup=AsyncMock())
        self.update = NS(effective_user=NS(id=42), effective_chat=NS(id=42, type='private'),
                         effective_message=self.message, callback_query=self.query)
        self.context = NS(user_data={}, args=[])

    def run_async(self, coroutine):
        try:
            coroutine.send(None)
        except StopIteration as done:
            return done.value
        finally:
            coroutine.close()
        self.fail('Test coroutine unexpectedly required live asynchronous IO')

    def text(self):
        return '\n'.join(call.args[0] for call in self.message.reply_text.call_args_list)

    def click(self, data):
        self.query.data = data
        self.run_async(self.controller.callback(self.update, self.context))

    def begin_edit(self, key):
        self.run_async(self.controller.update_profile(self.update, self.context))
        state = self.context.user_data[STATE_KEY]
        self.click(f"field:{state['token']}:{key}")
        return state

    def test_privacy_notice_precedes_id_and_command_id_is_not_processed(self):
        from config.privacy import PRIVACY_NOTICE
        self.bots.get_student_id.return_value = Error("Not logged in")
        self.context.args = ["1234567"]
        self.controller._send_otp = Mock(return_value=Success("Sent"))
        self.run_async(self.controller.login(self.update, self.context))
        messages = [call.args[0] for call in self.message.reply_text.call_args_list]
        self.assertEqual(messages[0], PRIVACY_NOTICE)
        self.assertIn("What is your student ID", messages[1])
        self.controller._send_otp.assert_not_called()
        self.assertTrue(self.context.user_data["awaiting_student_id"])
        self.run_async(self.controller.text(self.update, self.context, raw="1234567"))
        self.controller._send_otp.assert_called_once_with("1234567")

    def test_bio_warning_is_shown_when_editing_in_telegram(self):
        from config.privacy import BIO_PRIVACY_WARNING
        self.begin_edit("bio")
        self.assertIn(BIO_PRIVACY_WARNING, self.text())

    def test_bot_import_does_not_connect_to_database(self):
        with patch('Data_Manager.database.database_connection.DatabaseConnection.create_pool') as create:
            import tele.bot
            importlib.reload(tele.bot)
            create.assert_not_called()

    def test_handlers_cover_main_menu_and_legacy_aliases(self):
        application = Mock()
        self.controller.register(application)
        commands = set()
        for call in application.add_handler.call_args_list:
            commands.update(getattr(call.args[0], 'commands', []))
        self.assertTrue({'login','otp','setup','profile','update','matches','connections',
                         'delete_account','logout','quit','menu','find_match','view_matches'} <= commands)
        application.add_error_handler.assert_called_once()

    def test_login_rejects_invalid_id_before_email(self):
        self.bots.get_student_id.return_value = Error('not linked')
        self.context.args = ['123']
        self.controller._send_otp = Mock()
        self.run_async(self.controller.login(self.update, self.context))
        self.controller._send_otp.assert_not_called()
        self.assertIn('7 digits', self.text())

    def test_otp_is_bound_to_pending_id_and_limited_to_three_attempts(self):
        import time
        self.context.user_data['pending_login'] = {'student_id':'1234567','chat_id':42,
            'attempts':0,'created':time.monotonic()}
        self.context.args = ['7654321', '0000']
        self.run_async(self.controller.otp(self.update, self.context))
        self.otp.verify_otp.assert_not_called()
        self.context.args = ['0000']
        self.otp.verify_otp.return_value = Error('OTP Mismatch')
        for _ in range(3):
            self.run_async(self.controller.otp(self.update, self.context))
        self.assertNotIn('pending_login', self.context.user_data)
        self.assertEqual(self.otp.verify_otp.call_count, 3)
        self.bots.add_bot.assert_not_called()

    def test_verified_new_user_enters_profile_creation(self):
        import time
        self.context.user_data['pending_login'] = {'student_id':'1234567','chat_id':42,
            'attempts':0,'created':time.monotonic()}
        self.context.args = ['4321']
        self.otp.verify_otp.return_value = Success('verified')
        self.users.get_profile.return_value = Success(Profile(student_id='1234567'))
        self.run_async(self.controller.otp(self.update, self.context))
        self.bots.add_bot.assert_called_once_with('1234567', 42)
        self.assertEqual(self.context.user_data[STATE_KEY]['field'], 'name')

    def test_full_profile_creation_saves_only_after_confirmation(self):
        self.users.get_profile.return_value = Success(Profile(student_id='1234567'))
        self.run_async(self.controller.setup(self.update, self.context))
        state = self.context.user_data[STATE_KEY]
        answers = {'name':'Clint','birthday':'15/06/2005','gender':'1','year':'1','course':'1',
            'match_preference':'1','here_for':'Friends','telegram_handle':'@example','hobbies':'Coding'}
        while state['phase'] == 'question':
            key = state['field']
            self.run_async(self.controller.text(self.update, self.context, raw=answers.get(key, '')))
        self.assertEqual(state['phase'], 'review')
        self.users.update_user.assert_not_called()
        def persist(student_id, fields):
            self.users.get_profile.return_value = Success(Profile.from_dict({'student_id':student_id, **fields}))
            return Success('saved')
        self.users.update_user.side_effect = persist
        self.run_async(self.controller.save(self.update, self.context))
        self.users.update_user.assert_called_once()
        values = self.users.update_user.call_args.args[1]
        self.assertNotIn('birthday', values)
        self.assertIsInstance(values['age'], int)
        self.assertEqual(values['horoscope'], 'Gemini')
        self.assertNotIn(STATE_KEY, self.context.user_data)

    def test_race_edit_changes_own_race_not_blacklist(self):
        state = self.begin_edit('race')
        self.run_async(self.controller.text(self.update, self.context, raw='Chinese'))
        self.assertEqual(state['profile']['race'], 'Chinese')
        self.assertEqual(state['profile']['race_preference'], [])
        self.users.update_user.assert_not_called()
        self.run_async(self.controller.save(self.update, self.context))  # Review only.
        self.users.update_user.assert_not_called()
        self.run_async(self.controller.save(self.update, self.context))  # Confirm.
        values = self.users.update_user.call_args.args[1]
        self.assertEqual(values['race'], 'Chinese')
        self.assertEqual(values['dealbreakers']['race'], [])

    def test_blacklist_buttons_allow_multiple_values(self):
        state = self.begin_edit('race_preference')
        for index in (1, 2):
            self.click(f"answer:{state['token']}:{state['revision']}:{index}")
        self.click(f"answer:{state['token']}:{state['revision']}:done")
        self.assertEqual(state['profile']['race_preference'], ['Chinese', 'Malay'])
        values = self.controller._form.storage_values(state['profile'])
        self.assertEqual(values['dealbreakers']['race'], ['Chinese', 'Malay'])

    def test_age_range_validation_and_friendship_skip_rules(self):
        state = self.begin_edit('max_preferred_age')
        state['profile']['min_preferred_age'] = 23
        self.run_async(self.controller.text(self.update, self.context, raw='20'))
        self.assertIn('cannot exceed', self.text())
        self.assertIsNone(state['profile']['max_preferred_age'])
        self.run_async(self.controller.text(self.update, self.context, raw='25'))
        self.click(f"field:{state['token']}:here_for")
        self.run_async(self.controller.text(self.update, self.context, raw='Friends'))
        self.assertIsNone(state['profile']['expectations'])
        self.click(f"field:{state['token']}:expectations")
        self.assertIsNone(state['field'])

    def test_course_is_typed_and_old_buttons_do_not_change_answer(self):
        state = self.begin_edit('course')
        self.assertIn('Reply with the course number', self.text())
        self.run_async(self.controller.text(self.update, self.context, raw='1'))
        self.assertEqual(state['profile']['course'], next(f for f in PROFILE_FIELDS if f['key']=='course')['options'][0])
        self.click(f"answer:oldtoken:oldrevision:0")
        self.assertIn('expired', self.text())

    def test_save_failure_keeps_draft_and_cancel_discards_it(self):
        state = self.begin_edit('bio')
        self.run_async(self.controller.text(self.update, self.context, raw='Enjoy coding'))
        self.run_async(self.controller.save(self.update, self.context))
        self.users.update_user.side_effect = RuntimeError('Offline')
        with patch('IO_Manager.telegram.profile_setup.logger.exception'):
            self.run_async(self.controller.save(self.update, self.context))
        self.assertIs(self.context.user_data[STATE_KEY], state)
        self.assertEqual(state['profile']['bio'], 'Enjoy coding')
        self.users.update_user.side_effect = None
        self.run_async(self.controller.save(self.update, self.context))
        self.assertNotIn(STATE_KEY, self.context.user_data)
        self.begin_edit('bio')
        self.run_async(self.controller.cancel(self.update, self.context))
        self.assertNotIn(STATE_KEY, self.context.user_data)

    def test_profile_display_matches_console_and_has_no_birthday(self):
        from IO_Manager.console_io import ConsoleIO
        lines = []
        values = self.controller._form.form_values(self.profile)
        ConsoleIO(write=lines.append).show_profile(values)
        self.run_async(self.controller.profile(self.update, self.context))
        self.assertIn('\n'.join(lines), self.text())
        self.assertNotIn('Birthday:', self.text())
        self.assertIn('Age:', self.text())

    def test_accept_reject_advance_and_stale_clicks_are_rejected(self):
        candidates = [Candidate(student_id=s, name='Example', compatibility_score=80, reason='Shared hobby') for s in ('B','C')]
        self.controller._recommendations = Mock()
        self.controller._recommendations.get_recommendations.return_value = Success(candidates)
        self.controller._recommendations.eligible_users.return_value = Success(candidates)
        self.matches.handle_candidate_decision.return_value = Success('saved')
        self.run_async(self.controller.matches(self.update, self.context))
        state = self.context.user_data['browse']
        token = state['token']
        self.click(f'match:{token}:accept')
        self.matches.handle_candidate_decision.assert_called_once_with('1234567','B',True)
        self.assertEqual(state['current'], 'C')
        self.click(f'match:{token}:accept')
        self.assertEqual(self.matches.handle_candidate_decision.call_count, 1)
        self.click(f"match:{state['token']}:reject")
        self.assertEqual(self.matches.handle_candidate_decision.call_args.args, ('1234567','C',False))
        self.assertNotIn('browse', self.context.user_data)

    def test_failed_decision_can_retry_and_preferences_are_rechecked(self):
        candidate = Candidate(student_id='B', compatibility_score=80)
        self.controller._recommendations = Mock()
        self.controller._recommendations.get_recommendations.return_value = Success([candidate])
        self.controller._recommendations.eligible_users.return_value = Success([candidate])
        self.run_async(self.controller.matches(self.update, self.context))
        token = self.context.user_data['browse']['token']
        self.matches.handle_candidate_decision.return_value = Error('Could not save')
        self.click(f'match:{token}:accept')
        self.assertEqual(self.context.user_data['browse']['token'], token)
        self.controller._recommendations.eligible_users.return_value = Success([])
        self.click(f'match:{token}:accept')
        self.assertEqual(self.matches.handle_candidate_decision.call_count, 1)
        self.assertNotIn('browse', self.context.user_data)

    def test_connections_show_all_contacts_when_suggestions_fail(self):
        self.suggestions.get_matches_for_user.return_value = [
            {'success':False,'user_b_info':{'name':name,'tele_handle':handle,'insta_handle':'@photo'}}
            for name,handle in [('One','@one'),('Two','@two')]]
        self.run_async(self.controller.connections(self.update, self.context))
        self.assertIn('@one', self.text())
        self.assertIn('@two', self.text())
        self.assertIn('@photo', self.text())
        self.assertIn('temporarily unavailable', self.text())

    def begin_suggestion_review(self):
        result = dict(success=True, user_a="1234567", user_b="7654321",
            user_b_info={"name": "Example", "tele_handle": "@example"},
            compatibility={"compatibility_score": 80},
            common_interests=["Coding"], conversation_starters=["What do you build?"],
            outing_ideas=["Library"])
        self.suggestions.get_matches_for_user.return_value = [result]
        self.run_async(self.controller.connections(self.update, self.context))
        return next(iter(self.context.user_data["suggestion_reviews"])), result

    def test_regenerate_suggestions_uses_feedback_and_expires_old_buttons(self):
        token, previous = self.begin_suggestion_review()
        updated = {**previous, "outing_ideas": ["Park"]}
        self.suggestions.regenerate_for_connection.return_value = updated
        self.click(f"suggest:{token}:redo")
        self.run_async(self.controller.text(self.update, self.context, raw="Outdoor ideas"))
        self.suggestions.regenerate_for_connection.assert_called_once_with(
            "1234567", "7654321", "Outdoor ideas", previous)
        self.assertIn("Park", self.text())
        self.assertIn("@example", self.text())
        self.assertNotIn(token, self.context.user_data["suggestion_reviews"])
        self.click(f"suggest:{token}:redo")
        self.assertIn("expired", self.text())

    def test_suggestion_failures_preserve_results_and_limit_attempts(self):
        token, previous = self.begin_suggestion_review()
        self.suggestions.regenerate_for_connection.return_value = {"success": False}
        for attempt in range(3):
            token = next(iter(self.context.user_data["suggestion_reviews"]))
            self.click(f"suggest:{token}:redo")
            self.run_async(self.controller.text(self.update, self.context, raw="Different ideas"))
        self.assertEqual(self.suggestions.regenerate_for_connection.call_count, 3)
        self.assertEqual(self.context.user_data["suggestion_reviews"], {})
        self.assertIn("Regeneration limit reached", self.text())
        self.assertIn("Library", self.text())
        self.assertEqual(previous["outing_ideas"], ["Library"])

    def test_suggestion_feedback_validation_cancel_keep_and_chat_binding(self):
        token, previous = self.begin_suggestion_review()
        self.update.effective_chat.id = 99
        self.click(f"suggest:{token}:redo")
        self.assertNotIn("suggestion_feedback", self.context.user_data)
        self.update.effective_chat.id = 42
        self.click(f"suggest:{token}:redo")
        for raw in ("", "x" * 501):
            self.run_async(self.controller.text(self.update, self.context, raw=raw))
        self.suggestions.regenerate_for_connection.assert_not_called()
        self.run_async(self.controller.text(self.update, self.context, raw="0"))
        self.assertNotIn("suggestion_feedback", self.context.user_data)
        self.click(f"suggest:{token}:keep")
        self.assertNotIn(token, self.context.user_data["suggestion_reviews"])
        self.suggestions.regenerate_for_connection.assert_not_called()

    def test_other_user_cannot_use_suggestion_buttons(self):
        token, previous = self.begin_suggestion_review()
        self.bots.get_student_id.return_value = Success("9999999")
        self.click(f"suggest:{token}:redo")
        self.assertNotIn("suggestion_feedback", self.context.user_data)
        self.suggestions.regenerate_for_connection.assert_not_called()

    def test_delete_requires_confirmation_and_authentication(self):
        self.run_async(self.controller.delete_account(self.update, self.context))
        self.users.delete_user.assert_not_called()
        token = self.context.user_data['delete']['token']
        self.click(f'delete:{token}:no')
        self.users.delete_user.assert_not_called()
        self.run_async(self.controller.delete_account(self.update, self.context))
        token = self.context.user_data['delete']['token']
        self.users.delete_user.return_value = Success('deleted')
        self.click(f'delete:{token}:yes')
        self.users.delete_user.assert_called_once_with('1234567')
        self.assertEqual(self.context.user_data, {})
        self.bots.get_student_id.return_value = Error('not linked')
        self.click(f'delete:{token}:yes')
        self.assertEqual(self.users.delete_user.call_count, 1)

    def test_other_user_cannot_use_menu_and_logout_clears_drafts(self):
        self.click('nav:99:delete')
        self.users.delete_user.assert_not_called()
        self.assertIn('another user', self.text())
        self.context.user_data[STATE_KEY] = {'profile': {}}
        self.run_async(self.controller.logout(self.update, self.context))
        self.assertEqual(self.context.user_data, {})
        self.assertIn('Goodbye', self.text())

    def test_guard_reports_error_without_discarding_draft(self):
        self.context.user_data[STATE_KEY] = {'profile': {'bio':'Draft'}}
        handler = AsyncMock(side_effect=RuntimeError('Offline'))
        handler.__name__ = 'test_handler'
        with patch('IO_Manager.telegram.telegram_app.logger.exception'):
            self.run_async(self.controller._guard(handler)(self.update, self.context))
        self.assertEqual(self.context.user_data[STATE_KEY]['profile']['bio'], 'Draft')
        self.assertIn('Please retry', self.text())

    def test_bot_service_does_not_report_failed_logout_as_success(self):
        from Logic_Manager.services.bot_service import BotService
        repo = Mock()
        repo.remove_bot.return_value = False
        self.assertFalse(BotService(repo).logout(42).success)
