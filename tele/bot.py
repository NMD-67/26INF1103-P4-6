from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    MenuButtonCommands,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)
from dotenv import load_dotenv
from pathlib import Path
import os
import secrets
from telegram.error import TelegramError
from IO_Manager import io_manager
from tele import profile_setup
import traceback
from datetime import datetime

from Data_Manager.database.connection import create_connection_pool
from services.bot_service import BotRepo, BotService
from services.otp_service import OTPRepo, OTPService
from services.user_service import UserRepo, UserService, User
from services.match_service import MatchesRepo, MatchService
from models.candidate import Candidate
from config.user_fields import USER_FIELD_CONFIG

from Logic_Manager.Matching.matching_logic import get_next_user

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

pool = create_connection_pool()
user_repo = UserRepo(pool)
user_service = UserService(user_repo)
otp_repo = OTPRepo(pool)
otp_service = OTPService(otp_repo)
bot_repo = BotRepo(pool)
bot_service = BotService(bot_repo)
match_repo = MatchesRepo(pool)
match_service = MatchService(match_repo)

# Build the editable fields from the same questions used during setup.
USER_PROFILE_HANDLERS = {}
for field in profile_setup.PROFILE_FIELDS:
    if field["key"] == "student_id":
        continue  # A user cannot change the student ID linked to their login.
    editable_field = field.copy()
    editable_field["label"] = io_manager.profile_label(field["key"])
    USER_PROFILE_HANDLERS[field["key"]] = editable_field


def get_tele_id(update: Update):
    tele_id = update.effective_user.id
    return tele_id


async def send_msg(update: Update, message: str):
    await update.effective_message.reply_text(message)
    return


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(
        update,
        "Welcome to SITogether!\nUse /login <student_id> to log in, then /setup to complete your profile.",
    )


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, update.message.text)


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    bot_user = bot_service.get_student_id(tele_id)
    if bot_user.success:
        await send_msg(
            update,
            "You are already logged in! Use /setup to complete your profile or /profile to view it.",
        )
        return
    if len(context.args) != 1:
        await send_msg(update, "Usage: /login <student_id>")
        return

    student_id = context.args[0]
    # Call the login_user function from auth.py
    response = await otp_service.send_otp(student_id)
    if response.success:
        await send_msg(
            update,
            "An OTP has been sent to your email. Please check your inbox. \nEnter OTP using the /otp command:\n/otp <student_id> <otp>",
        )
    else:
        await send_msg(update, response.error_msg)


async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await send_msg(update, "Usage: /otp <student_id> <otp>")
        return

    student_id = context.args[0]
    otp = context.args[1]
    tele_id = get_tele_id(update)
    result = otp_service.verify_otp(student_id, otp, user_service)
    # print(f"opt res {result}")
    if result.success:
        bot_service.add_bot(student_id, tele_id)
        context.user_data.pop(profile_setup.STATE_KEY, None)
        context.user_data.pop("editing_field", None)
        await send_msg(update, "OTP verified! Send /setup to complete your profile.")
        return
    else:
        await send_msg(update, f"Error! {result.error_msg}")
        return


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    student_id = bot_repo.get_student_id(tele_id)

    if student_id is None:
        await send_msg(update, "You are not logged in! Log in using the /login command")
        return

    try:
        if student_id is None:
            await send_msg(update, "Student ID not found!")
            return
        # print("Getting user info")
        user_result = user_repo.get_profile(student_id)
        if user_result is None:
            await send_msg(update, "Error! User details not found")
            return
        user_details = user_result.get_user_details()
        reply = "User Details:\n"
        for key, value in user_details.items():
            if USER_FIELD_CONFIG.get(key) is not None:
                reply += f"{USER_FIELD_CONFIG[key].get("label")}: {io_manager.profile_value(key, value)}\n"

        btn_list = [
            [
                InlineKeyboardButton(
                    "Complete / redo profile setup", callback_data="profile_setup"
                )
            ]
        ]

        new_row = []
        for index, (key, value) in enumerate(USER_PROFILE_HANDLERS.items()):
            if len(new_row) >= 2:
                btn_list.append(new_row)
                new_row = []
            new_row.append(
                InlineKeyboardButton(
                    f"Edit {value['label']}", callback_data=f"edit_{key}"
                )
            )
            continue

        keyboard = InlineKeyboardMarkup(btn_list)

        await update.message.reply_text(reply, reply_markup=keyboard)
    except Exception as e:
        print(f"Error with /profile: {e}")
        traceback.print_exc()
        await send_msg(update, "An Error occurred, contact nmd_002")


async def edit_profile_button_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    if query.data == "profile_setup":
        await profile_setup.setup(update, context)
        return
    if profile_setup.STATE_KEY in context.user_data:
        await profile_setup.reply(
            update,
            "Finish /save or /cancel your draft before editing individual fields.",
        )
        return

    field = query.data
    print(f"query data: {field}")
    if field[5:] not in USER_PROFILE_HANDLERS:
        context.user_data.pop("editing_field", None)
        await query.message.reply_text(
            "This edit option is no longer available. Use /profile to refresh."
        )
        return
    try:
        user = bot_repo.get_student_id(get_tele_id(update))
    except Exception:
        await query.message.reply_text(
            "Could not check your login. Please try again later."
        )
        return
    if not user:
        await query.message.reply_text("Please /login before editing your profile.")
        return
    context.user_data["editing_field"] = field
    context.user_data["editing_token"] = secrets.token_hex(4)
    definition = USER_PROFILE_HANDLERS[field[5:]]
    print(f"definition: {definition}")
    lines = profile_setup.question_lines(definition)
    if profile_setup.uses_buttons(definition):
        token = context.user_data["editing_token"]
        prefix = f"editpick:{token}:{definition['key']}"
        width = 2
        if definition["kind"] == "mbti":
            width = 4
        keyboard = InlineKeyboardMarkup(
            profile_setup.option_rows(definition, prefix, width)
        )
        lines.append(
            "Tap your new answer below, or /cancel to keep the existing value."
        )
        await query.message.reply_text("\n".join(lines), reply_markup=keyboard)
        return
    lines.append("Send your new answer, or /cancel to keep the existing value.")
    await profile_setup.reply(update, "\n".join(lines))


async def edit_option_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        prefix, token, key, index = query.data.split(":")
        index = int(index)
    except (ValueError, AttributeError):
        await query.answer("This option is unavailable.")
        return
    definition = USER_PROFILE_HANDLERS.get(key)
    unavailable = "This menu is no longer active. Use /profile to edit again."

    # Only accept buttons from this user's current editing session.
    if prefix != "editpick":
        await query.answer(unavailable)
        return
    if profile_setup.STATE_KEY in context.user_data:
        await query.answer(unavailable)
        return
    if context.user_data.get("editing_field") != f"edit_{key}":
        await query.answer(unavailable)
        return
    if context.user_data.get("editing_token") != token:
        await query.answer(unavailable)
        return

    # Check the field and option before looking up the selected answer.
    if definition is None or not profile_setup.uses_buttons(definition):
        await query.answer(unavailable)
        return
    if not 0 <= index < len(definition["options"]):
        await query.answer(unavailable)
        return
    await query.answer()
    await text_handler(update, context, raw=definition["options"][index])
    if "editing_field" not in context.user_data:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except TelegramError:
            pass


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, raw=None):
    if profile_setup.STATE_KEY in context.user_data:
        await profile_setup.answer(update, context)
        return
    editing_field = context.user_data.get("editing_field")

    if not editing_field:
        return

    key = editing_field[5:]
    definition = USER_PROFILE_HANDLERS.get(key)
    if definition is None:
        context.user_data.pop("editing_field", None)
        await send_msg(update, "This field cannot be edited. Use /profile to refresh.")
        return
    if raw is None:
        raw = update.effective_message.text
    new_value, error = io_manager.validate_field(raw, definition)
    if error:
        await send_msg(
            update, f"{error}\nPlease try again, or /cancel to keep the existing value."
        )
        return
    try:
        student_id = bot_repo.get_student_id(get_tele_id(update))
        # response = user_repo.update(student_id)
        if definition.get("class") is not None:
            update_result = user_service.update_user(
                student_id, {definition.get("class"): {definition.get("key"): raw}}
            )
        else:
            if definition.get("key") == "birthday":
                new_value = datetime.strptime(new_value, "%d/%m/%Y").date()
            update_result = user_service.update_user(
                student_id=student_id, fields={definition.get("key"): new_value}
            )
        if update_result.success:
            await send_msg(update, "Updated!")
        else:
            await send_msg(update, update_result.error_msg)

    except Exception as e:
        traceback.print_exc()
        await send_msg(
            update, "Could not update your profile. Please try again, or /cancel."
        )
        return
    # if response["saved"]:
    #     context.user_data.pop("editing_field", None)
    #     context.user_data.pop("editing_token", None)
    #     await send_msg(update, "Profile updated. Use /profile to view it.")
    # else:
    #     message = response["message"]
    #     await send_msg(update, message + " Please retry your answer, or /cancel.")
    return


async def find_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    loading_message = await update.message.reply_text("Finding Matches...")
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )
    tele_id = get_tele_id(update)
    student_id = bot_repo.get_student_id(tele_id)
    if student_id is None:
        await loading_message.edit_text(
            "You are not logged in! Log in using the /login command"
        )
        return

    # Get next user
    # If empty, say ran out of ppl
    next_candidate_result = match_service.get_next_candidate(student_id)
    if not next_candidate_result.success:
        await loading_message.edit_text(
            f"An Error Occured when getting next candidate, {next_candidate_result.error_msg}"
        )
        return
    next_candidate = next_candidate_result.data
    if not isinstance(next_candidate, Candidate):
        await loading_message.edit_text(f"Error: Candidate not found!")
        return

    user_profile = ""
    for field in ["name", "year", "course", "bio", "here_for", "hobbies"]:
        if getattr(next_candidate, field, None):
            user_profile += (
                f"{io_manager.profile_label(field)}: {getattr(next_candidate, field)}\n"
            )

    # TODO: Handle accept/reject
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "👍", callback_data=f"accept_{next_candidate.student_id}"
                ),
                InlineKeyboardButton(
                    "👎", callback_data=f"reject_{next_candidate.student_id}"
                ),
            ],
        ]
    )

    await loading_message.edit_text(user_profile, reply_markup=keyboard)
    # Get student profile with student_id
    # Display the student
    # Give options "👍" or "👎"
    # If 👍, add to accepted student id -> Check if mutual


async def user_accept_handler(update: Update, ContextType: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = bot_repo.get_student_id(get_tele_id(update))

    candidate_id = query.data.split("_", 1)[1]
    match_service.handle_candidate_decision(
        student_id=student_id, candidate_id=candidate_id, accepted=True
    )

    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(f"Accepted!")


async def user_reject_handler(update: Update, ContextType: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    student_id = bot_repo.get_student_id(get_tele_id(update))

    candidate_id = query.data.split("_", 1)[1]
    match_result = match_service.handle_candidate_decision(
        student_id=student_id, candidate_id=candidate_id, accepted=False
    )

    if not match_result.success:
        await query.message.reply_text(f"An error occurred: {match_result.error_msg}")
    else:
        await query.message.reply_text(f"Rejected! Use /find_match to view next user!")

    await query.edit_message_reply_markup(reply_markup=None)


async def view_matches_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_id = bot_repo.get_student_id(get_tele_id(update))

    matches_response = match_service.get_all_matches(student_id)
    if not matches_response.success:
        await send_msg(update, "An error occurred when getting matches")
        return
    match_list = matches_response.data
    if len(match_list) < 1:
        await send_msg(update, "Wow, such empty...")
        return
    match_text = ""
    match_data = match_list[0].get_user_details()
    for field, value in match_data.items():
        match_text += f"{field}: {value}"
    await send_msg(update, match_text)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(
        update,
        "COMMANDS\n/login <student_id>: Log in\n/otp <student_id> <otp>: Verify login\n/setup: Complete or redo your profile\n/skip: Skip an optional setup question\n/save: Save the completed draft\n/cancel: Discard the draft\n/profile: View your profile",
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    remove_bot_result = bot_service.logout(tele_id)
    if remove_bot_result.success:
        return await send_msg(update, "Logged out sucessfully!")
    else:
        return await send_msg(update, remove_bot_result.error_msg)


async def delete_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    student_id = bot_service.get_student_id(get_tele_id(update)).data

    delete_user_result = user_service.delete_user(student_id)
    if delete_user_result.success:
        return await send_msg(update, "Account deleted")
    else:
        return await send_msg(update, delete_user_result.error_msg)


async def configure_command_menu(application):
    """Publish the command list used by Telegram's built-in Menu button."""
    await application.bot.set_my_commands(
        [
            BotCommand("profile", "View your profile"),
            BotCommand("setup", "Create or redo your profile"),
            BotCommand("login", "Log in with your student ID"),
            BotCommand("otp", "Verify your email login code"),
            BotCommand("skip", "Skip an optional setup question"),
            BotCommand("save", "Save your completed profile"),
            BotCommand("cancel", "Cancel your current draft"),
            BotCommand("help", "Show instructions and commands"),
            BotCommand("start", "Show the welcome message"),
            BotCommand("find_match", "View reccomended profiles"),
            BotCommand("view_matches", "View users that've matched with you!"),
            BotCommand("logout", "Log out of your account"),
            BotCommand("delete_account", "Delete Account"),
        ]
    )
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


def run_bot():
    builder = ApplicationBuilder()
    builder.token(os.environ.get("TELE_API_KEY"))
    builder.post_init(configure_command_menu)
    app = builder.build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("login", login))
    app.add_handler(CommandHandler("otp", otp))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("setup", profile_setup.setup))
    app.add_handler(CommandHandler("skip", profile_setup.skip))
    app.add_handler(CommandHandler("save", profile_setup.save))
    app.add_handler(CommandHandler("cancel", profile_setup.cancel))
    app.add_handler(CommandHandler("find_match", find_match_handler))
    app.add_handler(CommandHandler("view_matches", view_matches_handler))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("delete_account", delete_account))
    app.add_handler(CallbackQueryHandler(profile_setup.menu_choice, pattern=r"^form:"))
    app.add_handler(CallbackQueryHandler(edit_option_handler, pattern=r"^editpick:"))
    app.add_handler(
        CallbackQueryHandler(
            edit_profile_button_handler, pattern=r"^(profile_setup|edit_.*)$"
        )
    )
    app.add_handler(CallbackQueryHandler(user_accept_handler, pattern=r"^accept_"))
    app.add_handler(CallbackQueryHandler(user_reject_handler, pattern=r"^reject_"))

    app.add_handler(CommandHandler("help", help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    io_manager.show("Starting the bot...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
