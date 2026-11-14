"""Run the Telegram adapter: python -m tele.bot. Importing this module is offline."""
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder

logger = logging.getLogger(__name__)


def build_application(controller, token):
    application = (ApplicationBuilder().token(token).concurrent_updates(False)
                   .post_init(controller.configure_menu).build())
    controller.register(application)
    return application


def run_bot():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    token = (os.getenv("TELE_API_KEY") or "").strip()
    if not token:
        raise RuntimeError("TELE_API_KEY is missing")
    from Data_Manager.database.database_connection import DatabaseConnection
    from repositories.user_repo import UserRepo
    from repositories.otp_repo import OTPRepo
    from repositories.bot_repo import BotRepo
    from repositories.matches_repo import MatchesRepo
    from services.user_service import UserService
    from services.otp_service import OTPService
    from services.bot_service import BotService
    from services.match_service import MatchService
    from AI_Manager.Profile_Matching.lazy_groq_scorer import LazyGroqScorer
    from AI_Manager.Suggestions_generator import SuggestionsGenerator, ConnectionSuggestionService
    from tele.telegram_app import TelegramApp

    pool = DatabaseConnection().create_pool()
    scoring = LazyGroqScorer()
    generator = None
    loop = None
    try:
        users = UserService(UserRepo(pool))
        matches = MatchService(MatchesRepo(pool))
        generator = SuggestionsGenerator.from_environment()
        controller = TelegramApp(users, OTPService(OTPRepo(pool)), BotService(BotRepo(pool)),
                                 matches, scoring, ConnectionSuggestionService(matches, users, generator))
        application = build_application(controller, token)
        # Python 3.14 no longer creates an event loop implicitly.
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("Starting the bot...")
        application.run_polling(close_loop=False)
    finally:
        try:
            if generator is not None:
                generator.close()
        finally:
            try:
                scoring.close()
            finally:
                pool.close()
                if loop is not None:
                    loop.close()
                    asyncio.set_event_loop(None)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    try:
        run_bot()
    except (KeyboardInterrupt, EOFError):
        print("Bot stopped.")
    except Exception:
        logger.exception("Telegram startup failed")
        print("Could not start the bot. Check configuration and logs.")
