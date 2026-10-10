from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, MenuButtonCommands
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from pathlib import Path
import os
import asyncio
import secrets
from telegram.error import TelegramError
import io_manager
from database import db
from tele import profile_setup

from database.db import save_user, get_bot_user
from src.auth import login_user, validate_otp, get_user_info

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

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
    await send_msg(update, "Welcome to SITogether!\nUse /login <student_id> to log in, then /setup to complete your profile.")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, update.message.text)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    bot_user = get_bot_user(tele_id)
    if bot_user is not None:
        await send_msg(update, "You are already logged in! Use /setup to complete your profile or /profile to view it.")
        return
    if len(context.args) != 1:
        await send_msg(update, "Usage: /login <student_id>")
        return

    student_id = context.args[0]
    # Call the login_user function from auth.py
    response = await login_user(student_id)
    if response == 400:
        await send_msg(update, "Invalid student ID. Please try again.")
    elif response == 500:
        await send_msg(update, "Error occurred while sending OTP. Please try again later.")
    else:
        await send_msg(update, "An OTP has been sent to your email. Please check your inbox. \nEnter OTP using the /otp command:\n/otp <student_id> <otp>")

async def otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await send_msg(update, "Usage: /otp <student_id> <otp>")
        return
    
    student_id = context.args[0]
    otp = context.args[1]
    tele_id = get_tele_id(update)
    result = validate_otp(student_id=student_id, otp=otp)
    print(f"opt res {result}")
    if result == 200:
        save_user(tele_id, student_id)
        context.user_data.pop(profile_setup.STATE_KEY, None)
        context.user_data.pop("editing_field", None)
        await send_msg(update, "OTP verified! Send /setup to complete your profile.")
        return
    if result == 201:
        save_user(tele_id, student_id)
        context.user_data.pop(profile_setup.STATE_KEY, None)
        context.user_data.pop("editing_field", None)
        await send_msg(update, "Account created! Send /setup to complete your profile.")
        return
    if result == 400:
        await send_msg(update, "Invalid student ID. Please try again.")
    elif result == 403:
        await send_msg(update, "Invalid OTP!")
        return
    elif result == 404:
        await send_msg(update, "Error! OTP not found")
        return
    elif result == 500:
        await send_msg(update, "A server error! Contact @nmd_002 for help")
        return
    else:
        await send_msg(update, "An unknown error! Contact @nmd_002 for help")
        return

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    user = get_bot_user(tele_id)

    if user is None:
        await send_msg(update, "You are not logged in! Log in using the /login command")
        return

    try:
      student_id = user["student_id"]
      if student_id is None:
          await send_msg(update, "Student ID not found!")
          return
      print("Getting user info")
      user_result = get_user_info(student_id)
      if user_result is None or user_result.get("status") == 404:
          await send_msg(update, "Error! User details not found")
          return
      user_details = user_result["user"]
      reply = "User Details:\n"
      for key, value in user_details.items():
          reply += f"{io_manager.profile_label(key)}: {io_manager.profile_value(key, value)}\n"

      btn_list = [[InlineKeyboardButton("Complete / redo profile setup", callback_data="profile_setup")]]

      for key, value in USER_PROFILE_HANDLERS.items():
          btn_list.append([InlineKeyboardButton(f"Edit {value['label']}", callback_data=f"edit_{key}")])

      keyboard = InlineKeyboardMarkup(btn_list)

      await update.message.reply_text(reply, reply_markup=keyboard)
    except Exception as e:
        print(f"Error with /profile: {e}")
        await send_msg(update, "An Error occurred, contact nmd_002")

async def edit_profile_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "profile_setup":
        await profile_setup.setup(update, context)
        return
    if profile_setup.STATE_KEY in context.user_data:
        await profile_setup.reply(update, "Finish /save or /cancel your draft before editing individual fields.")
        return

    field = query.data
    if field[5:] not in USER_PROFILE_HANDLERS:
        context.user_data.pop("editing_field", None)
        await query.message.reply_text("This edit option is no longer available. Use /profile to refresh.")
        return
    try:
        user = await asyncio.to_thread(get_bot_user, get_tele_id(update))
    except Exception:
        await query.message.reply_text("Could not check your login. Please try again later.")
        return
    if not user:
        await query.message.reply_text("Please /login before editing your profile.")
        return
    context.user_data["editing_field"] = field
    context.user_data["editing_token"] = secrets.token_hex(4)
    definition = USER_PROFILE_HANDLERS[field[5:]]
    lines = profile_setup.question_lines(definition)
    if profile_setup.uses_buttons(definition):
        token = context.user_data["editing_token"]
        prefix = f"editpick:{token}:{definition['key']}"
        width = 2
        if definition["kind"] == "mbti":
            width = 4
        keyboard = InlineKeyboardMarkup(profile_setup.option_rows(definition, prefix, width))
        lines.append("Tap your new answer below, or /cancel to keep the existing value.")
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
        await send_msg(update, f"{error}\nPlease try again, or /cancel to keep the existing value.")
        return
    try:
        user = await asyncio.to_thread(get_bot_user, get_tele_id(update))
        if not user:
            context.user_data.pop("editing_field", None)
            await send_msg(update, "Please /login before editing your profile.")
            return
        response = await asyncio.to_thread(
            db.save_profile,
            {"student_id": str(user["student_id"]), key: new_value}, partial=True)
    except Exception:
        await send_msg(update, "Could not update your profile. Please try again, or /cancel.")
        return
    if response["saved"]:
        context.user_data.pop("editing_field", None)
        context.user_data.pop("editing_token", None)
        await send_msg(update, "Profile updated. Use /profile to view it.")
    else:
        message = response["message"]
        await send_msg(update, message + " Please retry your answer, or /cancel.")
    return

async def find_match_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, "Finding Matches...")

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, "COMMANDS\n/login <student_id>: Log in\n/otp <student_id> <otp>: Verify login\n/setup: Complete or redo your profile\n/skip: Skip an optional setup question\n/save: Save the completed draft\n/cancel: Discard the draft\n/profile: View your profile")

async def configure_command_menu(application):
    """Publish the command list used by Telegram's built-in Menu button."""
    await application.bot.set_my_commands([
        BotCommand("profile", "View your profile"),
        BotCommand("setup", "Create or redo your profile"),
        BotCommand("login", "Log in with your student ID"),
        BotCommand("otp", "Verify your email login code"),
        BotCommand("skip", "Skip an optional setup question"),
        BotCommand("save", "Save your completed profile"),
        BotCommand("cancel", "Cancel your current draft"),
        BotCommand("help", "Show instructions and commands"),
        BotCommand("start", "Show the welcome message"),
        BotCommand("find_match", "View reccomended profiles")
    ])
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
    app.add_handler(CallbackQueryHandler(profile_setup.menu_choice, pattern=r"^form:"))
    app.add_handler(CallbackQueryHandler(edit_option_handler, pattern=r"^editpick:"))
    app.add_handler(CallbackQueryHandler(edit_profile_button_handler, pattern=r"^(profile_setup|edit_.*)$"))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    io_manager.show("Starting the bot...")
    app.run_polling()


if __name__ == "__main__":
    run_bot()
