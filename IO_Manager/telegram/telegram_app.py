"""Telegram commands and sessions for the same services used by the CLI."""
import asyncio
import logging
import secrets
import time
from telegram import BotCommand, MenuButtonCommands
from telegram.error import TelegramError
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config.user_fields import PROFILE_FIELDS
from config.privacy import PRIVACY_NOTICE
from IO_Manager.profile_validator import ProfileValidator
from IO_Manager.profile_form import ProfileForm
from Logic_Manager.services.recommendation_service import RecommendationService
from IO_Manager.telegram.profile_setup import TelegramProfileForm, STATE_KEY
from IO_Manager.telegram.telegram_io import TelegramIO

logger = logging.getLogger(__name__)


class TelegramApp:
    def __init__(self, users, otp, bots, matches, scoring, suggestions):
        self._users = users
        self._otp = otp
        self._bots = bots
        self._matches = matches
        self._io = TelegramIO()
        self._form = ProfileForm()
        self._drafts = TelegramProfileForm(users, self._io, self._form)
        self._recommendations = RecommendationService(users, matches, scoring)
        self._suggestions = suggestions
        self._validator = ProfileValidator()

    async def _student(self, update, context):
        result = await asyncio.to_thread(self._bots.get_student_id, update.effective_user.id)
        if not result.success:
            await self._io.send(update, "Please /login first.")
            return None
        return str(result.data)

    async def _ready(self, update, context):
        sid = await self._student(update, context)
        if sid is None:
            return None
        result = await asyncio.to_thread(self._users.get_profile, sid)
        if not result.success:
            await self._io.send(update, result.error_msg + " Use /logout then /login if your account was deleted.")
            return None
        if self._form.missing_fields(self._form.form_values(result.data)):
            await self._io.send(update, "Please complete and save your profile first.")
            await self._drafts.begin(update, context, sid)
            return None
        return sid

    async def menu(self, update, context):
        sid = await self._ready(update, context)
        if sid is None:
            return
        owner = update.effective_user.id
        await self._io.send(update, "SITogether - choose an action:", [
            [("Find matches", f"nav:{owner}:matches"), ("View connections", f"nav:{owner}:connections")],
            [("My profile", f"nav:{owner}:profile"), ("Update profile", f"nav:{owner}:update")],
            [("Delete account", f"nav:{owner}:delete"), ("Quit / log out", f"nav:{owner}:logout")],
        ])

    async def start(self, update, context):
        result = await asyncio.to_thread(self._bots.get_student_id, update.effective_user.id)
        if result.success:
            await self.menu(update, context)
        else:
            await self._io.send(update, PRIVACY_NOTICE)
            await self._io.send(update, "Welcome to SITogether! Send /login to begin.")

    def _send_otp(self, sid):
        # OTPService also uses a blocking repository; run the whole operation off
        # the Telegram event loop. Its EmailSender handles SMTP asynchronously.
        return asyncio.run(self._otp.send_otp(sid))

    async def login(self, update, context):
        existing = await asyncio.to_thread(self._bots.get_student_id, update.effective_user.id)
        if existing.success:
            await self._io.send(update, "You are already logged in. Use /logout to change account.")
            await self.menu(update, context)
            return
        # Do not process command arguments before the user has seen the notice.
        context.user_data.pop("pending_login", None)
        await self._io.send(update, PRIVACY_NOTICE)
        context.user_data["awaiting_student_id"] = True
        await self._io.send(update, "What is your student ID? Enter 7 digits, or /cancel to stop.")

    async def _login_id(self, update, context, raw):
        field = next(f for f in PROFILE_FIELDS if f["key"] == "student_id")
        sid, error = self._validator.validate_field(raw, field)
        if error:
            context.user_data["awaiting_student_id"] = True
            await self._io.send(update, error + " Please try again.")
            return
        context.user_data.pop("pending_login", None)
        result = await asyncio.to_thread(self._send_otp, sid)
        if not result.success:
            await self._io.send(update, result.error_msg)
            return
        context.user_data.pop("awaiting_student_id", None)
        context.user_data["pending_login"] = {"student_id": sid, "attempts": 0,
            "chat_id": update.effective_chat.id, "created": time.monotonic()}
        await self._io.send(update, "Check your school email for the OTP. Reply with the code, or use /otp <code>.")

    async def otp(self, update, context, code=None):
        pending = context.user_data.get("pending_login")
        if not pending or pending["chat_id"] != update.effective_chat.id:
            await self._io.send(update, "Request an OTP with /login in this chat first.")
            return
        if time.monotonic() - pending["created"] > 600:
            context.user_data.pop("pending_login", None)
            await self._io.send(update, "Login request expired. Use /login again.")
            return
        if code is None:
            args = context.args
            if len(args) == 2 and args[0] == pending["student_id"]:
                code = args[1]  # Compatibility with the old /otp ID CODE command.
            elif len(args) == 1:
                code = args[0]
            else:
                await self._io.send(update, "Use /otp <code> for the student ID you logged in with.")
                return
        pending["attempts"] += 1
        sid = pending["student_id"]
        result = await asyncio.to_thread(self._otp.verify_otp, sid, code.strip(), self._users)
        if not result.success:
            if pending["attempts"] >= 3:
                context.user_data.pop("pending_login", None)
                await self._io.send(update, "Login unsuccessful after 3 attempts. Use /login to request a new code.")
            else:
                await self._io.send(update, result.error_msg + " Please try again.")
            return
        context.user_data.pop("pending_login", None)
        linked = await asyncio.to_thread(self._bots.add_bot, sid, update.effective_user.id)
        if not linked.success:
            await self._io.send(update, "OTP verified, but Telegram login could not be saved. Use /login to retry.")
            return
        context.user_data.clear()
        await self._io.send(update, "OTP verified!")
        await self.menu(update, context)

    async def profile(self, update, context):
        sid = await self._ready(update, context)
        if sid is None:
            return
        result = await asyncio.to_thread(self._users.get_profile, sid)
        if not result.success:
            await self._io.send(update, result.error_msg)
            return
        await self._io.send(update, self._io.profile(self._form.form_values(result.data)))
        await self.menu(update, context)

    async def setup(self, update, context):
        sid = await self._student(update, context)
        if sid is not None:
            await self._drafts.begin(update, context, sid)

    async def update_profile(self, update, context):
        sid = await self._ready(update, context)
        if sid is not None:
            await self._drafts.begin(update, context, sid, editing=True)

    async def save(self, update, context):
        sid = await self._student(update, context)
        if sid is None:
            return
        state = self._drafts.state(update, context, sid)
        if state is None:
            await self._io.send(update, "No draft in this chat. Use /setup or /update.")
        elif await self._drafts.save(update, context, state):
            await self.menu(update, context)

    async def skip(self, update, context):
        if STATE_KEY not in context.user_data:
            await self._io.send(update, "There is no profile question to skip. Use /setup or /update.")
            return
        await self.text(update, context, raw="")

    async def cancel(self, update, context):
        context.user_data.clear()
        await self._io.send(update, "Current draft/action cancelled. Your saved profile is unchanged. Use /menu to continue.")

    async def text(self, update, context, raw=None):
        raw = update.effective_message.text if raw is None else raw
        if context.user_data.get("awaiting_student_id"):
            await self._login_id(update, context, raw)
        elif context.user_data.get("pending_login"):
            await self.otp(update, context, code=raw)
        elif STATE_KEY in context.user_data:
            sid = await self._student(update, context)
            if sid is None:
                return
            state = self._drafts.state(update, context, sid)
            if state is None:
                await self._io.send(update, "Use the chat where you opened the draft, or /cancel.")
            elif state["phase"] == "review" and raw.strip().lower() in ("y", "yes"):
                await self.save(update, context)
            elif state["phase"] == "review" and raw.strip().lower() in ("n", "no"):
                await self.cancel(update, context)
            else:
                await self._drafts.answer(update, state, raw)
        else:
            await self._io.send(update, "Use /menu to choose an action, or /login to get started.")

    async def matches(self, update, context):
        sid = await self._ready(update, context)
        if sid is None:
            return
        if STATE_KEY in context.user_data:
            await self._io.send(update, "Save or cancel your profile draft before browsing matches.")
            return
        context.user_data.pop("browse", None)
        await self._io.send(update, "Finding compatible profiles. Please wait...")
        result = await asyncio.to_thread(self._recommendations.get_recommendations, sid)
        if not result.success:
            await self._io.send(update, result.error_msg)
            return
        context.user_data["browse"] = {"student_id": sid, "chat_id": update.effective_chat.id,
                                      "rows": list(result.data), "token": None, "current": None}
        await self._show_next(update, context, sid)

    async def _show_next(self, update, context, sid):
        state = context.user_data.get("browse")
        if state is None:
            return
        eligible = await asyncio.to_thread(self._recommendations.eligible_users, sid)
        if not eligible.success:
            context.user_data.pop("browse", None)
            await self._io.send(update, eligible.error_msg)
            return
        allowed = {str(user.student_id) for user in eligible.data}
        while state["rows"]:
            candidate = state["rows"].pop(0)
            if str(candidate.student_id) not in allowed:
                continue
            state.update(current=str(candidate.student_id), token=secrets.token_hex(4))
            await self._io.send(update, self._io.candidate(candidate), [
                [("Accept", f"match:{state['token']}:accept"), ("Reject", f"match:{state['token']}:reject")],
                [("Return to menu", f"match:{state['token']}:menu")],
            ])
            return
        context.user_data.pop("browse", None)
        await self._io.send(update, "No new profiles match your current preferences. Use /menu to continue.")

    async def _decision(self, update, context, sid, parts):
        state = context.user_data.get("browse")
        if (not state or len(parts) != 3 or parts[1] != state["token"] or
            state["student_id"] != sid or state["chat_id"] != update.effective_chat.id):
            await self._io.send(update, "This recommendation menu has expired. Use /matches.")
            return
        if parts[2] == "menu":
            context.user_data.pop("browse", None)
            await self.menu(update, context)
            return
        if parts[2] not in ("accept", "reject"):
            return
        eligible = await asyncio.to_thread(self._recommendations.eligible_users, sid)
        if not eligible.success or state["current"] not in {str(u.student_id) for u in eligible.data}:
            context.user_data.pop("browse", None)
            await self._io.send(update, "This recommendation is no longer eligible. Use /matches to refresh.")
            return
        saved = await asyncio.to_thread(self._matches.handle_candidate_decision,
                                       sid, state["current"], parts[2] == "accept")
        if not saved.success:
            await self._io.send(update, saved.error_msg + " You can retry this decision.")
            return
        state["token"] = None  # Prevent replay before advancing.
        try:
            await update.callback_query.edit_message_reply_markup(reply_markup=None)
        except TelegramError:
            pass
        await self._io.send(update, "Decision saved.")
        await self._show_next(update, context, sid)

    async def connections(self, update, context):
        sid = await self._ready(update, context)
        if sid is None:
            return
        await self._io.send(update, "Loading mutual connections and suggestions...")
        results = await asyncio.to_thread(self._suggestions.get_matches_for_user, sid)
        if not results:
            await self._io.send(update, "No mutual connections yet.")
        for result in results:
            await self._io.send(update, self._io.connection(result))
        await self.menu(update, context)

    async def logout(self, update, context):
        linked = await asyncio.to_thread(self._bots.get_student_id, update.effective_user.id)
        if linked.success:
            result = await asyncio.to_thread(self._bots.logout, update.effective_user.id)
            if not result.success:
                await self._io.send(update, result.error_msg)
                return
        context.user_data.clear()
        await self._io.send(update, "Goodbye! Thanks for using SITogether. You are logged out.")

    async def delete_account(self, update, context):
        sid = await self._student(update, context)
        if sid is None:
            return
        token = secrets.token_hex(4)
        context.user_data["delete"] = {"student_id": sid, "token": token, "chat_id": update.effective_chat.id}
        await self._io.send(update, "Permanently delete your account?", [
            [("Yes, delete", f"delete:{token}:yes"), ("No", f"delete:{token}:no")],
        ])

    async def callback(self, update, context):
        query = update.callback_query
        await query.answer()
        parts = (query.data or "").split(":")
        if parts[0] == "nav" and len(parts) == 3:
            if parts[1] != str(update.effective_user.id):
                await self._io.send(update, "This menu belongs to another user. Open your own /menu.")
                return
            actions = {"matches": self.matches, "connections": self.connections,
                       "profile": self.profile, "update": self.update_profile,
                       "delete": self.delete_account, "logout": self.logout}
            if parts[2] in actions:
                await actions[parts[2]](update, context)
            return
        sid = await self._student(update, context)
        if sid is None:
            return
        if parts[0] in ("field", "answer", "draft"):
            state = self._drafts.state(update, context, sid)
            if state is None:
                await self._io.send(update, "No active draft here. Use /setup or /update.")
            elif await self._drafts.callback(update, context, state, parts):
                await self.menu(update, context)
        elif parts[0] == "match":
            await self._decision(update, context, sid, parts)
        elif parts[0] == "delete" and len(parts) == 3:
            state = context.user_data.get("delete")
            if not state or state != {"student_id": sid, "token": parts[1], "chat_id": update.effective_chat.id}:
                await self._io.send(update, "This confirmation has expired. Use /delete_account again.")
                return
            if parts[2] == "no":
                context.user_data.pop("delete", None)
                await self._io.send(update, "Deletion cancelled.")
                return
            if parts[2] != "yes":
                return
            result = await asyncio.to_thread(self._users.delete_user, sid)
            if not result.success:
                await self._io.send(update, result.error_msg)
                return
            context.user_data.clear()
            try:
                await asyncio.to_thread(self._bots.logout, update.effective_user.id)
            except Exception:
                logger.exception("Account deleted, but Telegram association cleanup failed")
            await self._io.send(update, "Account deleted. Goodbye!")
        else:
            await self._io.send(update, "This old menu is no longer supported. Use /menu.")

    async def help(self, update, context):
        await self._io.send(update,
            "/login [student_id] â€” log in with school email OTP\n"
            "/otp <code> â€” verify login\n/menu â€” show actions\n"
            "/setup â€” complete profile\n/profile â€” view profile\n/update â€” edit profile\n"
            "/skip â€” skip optional question\n/save â€” review/confirm draft\n/cancel â€” discard draft/action\n"
            "/matches â€” recommended profiles\n/connections â€” mutual contacts and suggestions\n"
            "/delete_account â€” confirm deletion\n/logout or /quit â€” leave the app")

    def _guard(self, handler):
        async def guarded(update, context):
            try:
                await handler(update, context)
            except Exception:
                logger.exception("Telegram operation failed: %s", handler.__name__)
                await self._io.send(update, "Could not complete this action. Please retry. Any unsaved profile draft is kept until /cancel, logout or restart.")
        return guarded

    async def on_error(self, update, context):
        # Never log the Update object: it may contain OTPs or profile answers.
        error = context.error
        logger.error("Telegram handler failed", exc_info=(type(error), error, error.__traceback__))
        if update is not None and update.effective_message is not None:
            try:
                await self._io.send(update, "The bot could not complete this action. Please try again later.")
            except TelegramError:
                logger.warning("Could not send Telegram error notice")

    async def configure_menu(self, application):
        await application.bot.set_my_commands([BotCommand(command, label) for command, label in (
            ("menu", "Main menu"), ("login", "Log in with school email OTP"),
            ("otp", "Verify OTP"), ("setup", "Complete profile"), ("profile", "My profile"),
            ("update", "Update profile"), ("matches", "Find matches"),
            ("connections", "Mutual connections and suggestions"), ("save", "Review and save draft"),
            ("skip", "Skip optional field"), ("cancel", "Cancel current action"),
            ("delete_account", "Delete account"), ("logout", "Log out"), ("help", "Help"),
        )])
        await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    def register(self, application):
        commands = {"start": self.start, "menu": self.menu, "login": self.login, "otp": self.otp,
            "setup": self.setup, "profile": self.profile, "update": self.update_profile,
            "skip": self.skip, "save": self.save, "cancel": self.cancel,
            "matches": self.matches, "find_match": self.matches,
            "connections": self.connections, "view_matches": self.connections,
            "logout": self.logout, "quit": self.logout, "delete_account": self.delete_account,
            "help": self.help}
        for command, handler in commands.items():
            application.add_handler(CommandHandler(command, self._guard(handler)))
        application.add_handler(CallbackQueryHandler(self._guard(self.callback)))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._guard(self.text)))
        application.add_error_handler(self.on_error)
