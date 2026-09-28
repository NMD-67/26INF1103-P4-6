from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
from pathlib import Path
import os


from src.auth import login_user

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")

print("Starting the bot...")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! I'm your bot. How can I assist you today?")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /login <student_id>")
        return

    student_id = context.args[0]
    # Call the login_user function from auth.py
    response = await login_user(student_id)
    if response == 400:
        await update.message.reply_text("Invalid student ID. Please try again.")
    elif response == 500:
        await update.message.reply_text("Error occurred while sending OTP. Please try again later.")
    else:
        await update.message.reply_text("An OTP has been sent to your email. Please check your inbox.")

app = ApplicationBuilder().token(os.environ.get("TELE_API_KEY")).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("login", login))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

app.run_polling()