from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
from dotenv import load_dotenv
from pathlib import Path
import os

from database.db import save_user, get_bot_user
from src.auth import login_user, validate_otp, get_user_info, edit_user_info

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

print("Starting the bot...")

USER_PROFILE_HANDLERS = {
    "name": {
        "label": "Name",
        "callback_data": "edit_name"
    },
    "birthday": {
        "label": "Birthday 🎂",
        "callback_data": "edit_birthday"
    },
    "gender": {
        "label": "Gender ⚤",
        "callback_data": "edit_gender"
    },
    "year": {
        "label": "Year",
        "callback_data": "edit_year"
    },
    "course": {
        "label": "Course 🎓",
        "callback_data": "edit_course"
    },
    "bio": {
        "label": "Bio",
        "callback_data": "edit_bio"
    },
    "religion": {
        "label": "Religion 🙏",
        "callback_data": "edit_religion"
    },
    "mbti": {
        "label": "MBTI",
        "callback_data": "edit_mbti"
    },
    "sexual_orientation": {
        "label": "Sexual Orientation",
        "callback_data": "edit_sexual_orientation"
    },
    "here_for": {
        "label": "Here For",
        "callback_data": "edit_here_for",
        "suggested_values": ["Friends", "Relationship"]
    },
    "expectation": {
        "label": "Expectation",
        "callback_data": "edit_expectation",
        "suggested_values": ["Short term", "Long term"]
    },
    "insta_handle": {
        "label": "Instagram Handle",
        "callback_data": "edit_insta_handle"
    },
    "cca": {
        "label": "CCA",
        "callback_data": "edit_cca",
        "is_list": True
    } 
}

def get_tele_id(update: Update):
    tele_id = update._effective_user.id
    return tele_id

async def send_msg(update: Update, message: str):
    await update.message.reply_text(message)
    return

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, "Welcome to SITogether!\nUse the /login command to get started!")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, update.message.text)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tele_id = get_tele_id(update)
    bot_user = get_bot_user(tele_id)
    if bot_user is not None:
        await send_msg(update, "You are already logged in!")
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
        await send_msg(update, "OTP verified!")
        return
    if result == 201:
        save_user(tele_id, student_id)
        await send_msg(update, "Account Created!")
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
      user_details = user_result["user"]
      reply = "User Details:\n"
      for key, value in user_details.items():
          reply += f"{key}: {value}\n"

      btn_list = []

      for key, value in USER_PROFILE_HANDLERS.items():
          btn_list.append([InlineKeyboardButton(f"Edit {value["label"]}", callback_data=f"edit_{key}")])

      keyboard = InlineKeyboardMarkup(btn_list)

      await update.message.reply_text(reply, reply_markup=keyboard)
    except Exception as e:
        print(f"Error with /profile: {e}")
        await send_msg(update, "An Error occurred, contact nmd_002")

async def edit_profile_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    field = query.data
    context.user_data["editing_field"] = field
    label = USER_PROFILE_HANDLERS[field[5:]]["label"]

    await query.message.reply_text(f"Please enter your new {label}")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    editing_field = context.user_data.get("editing_field")

    if editing_field:
        new_value = update.message.text
        tele_id = get_tele_id(update)
        student_id = get_bot_user(tele_id)["student_id"]

        for key, value in USER_PROFILE_HANDLERS.items():
            if editing_field == f"edit_{key}":
                response = edit_user_info(student_id, {key: new_value})
                print(f'response: {response}')
                if response["success"]:
                    await send_msg(update, "Updated Successfully!\nYou may use /profile to check your new profile!")
                    return
                else:
                    await send_msg(update, "An Error Occurred! :(")
                    return
                

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(update, "COMMANDS\n/login:\t Login to account\notp:\tEnter OTP after /login\n/profile:\tView Profile")

app = ApplicationBuilder().token(os.environ.get("TELE_API_KEY")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("login", login))
app.add_handler(CommandHandler("otp", otp))
app.add_handler(CommandHandler("profile", profile))
app.add_handler(CallbackQueryHandler(edit_profile_button_handler))
app.add_handler(CommandHandler("help", help))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling()