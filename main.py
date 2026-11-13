
"""Configure services and start SITogether."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from sitogether_app import SITogetherApp

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)


def main():
    # Import inside the startup boundary so configuration/import failures are logged.
    from Data_Manager.database.connection import create_connection_pool
    from repositories.user_repo import UserRepo
    from repositories.otp_repo import OTPRepo
    from repositories.matches_repo import MatchesRepo
    from services.user_service import UserService
    from services.otp_service import OTPService
    from services.match_service import MatchService
    from models.dealbreaker import DealBreaker
    from config.user_fields import USER_FIELD_CONFIG, PROFILE_FIELDS
    from IO_Manager.console_io import ConsoleIO
    from Logic_Manager.profile_logic_manager import ProfileLogicManager
    from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
    from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
    from AI_Manager.Suggestions_generator import (
        SuggestionsGenerator,
        ConnectionSuggestionService,
    )

    pool = create_connection_pool()
    key_pool = None
    try:
        users = UserService(UserRepo(pool))
        matches = MatchService(MatchesRepo(pool))
        otp = OTPService(OTPRepo(pool))
        key_pool = GroqKeyPool.from_env()
        scoring = GroqScorer(key_pool)
        suggestions_generator = SuggestionsGenerator.from_environment()
        suggestion_service = ConnectionSuggestionService(
            matches, users, suggestions_generator
        )
        logic = ProfileLogicManager(PROFILE_FIELDS)
        console = ConsoleIO(PROFILE_FIELDS, logic)
        app = SITogetherApp(
            users,
            otp,
            matches,
            scoring,
            suggestion_service,
            console,
            logic,
            USER_FIELD_CONFIG,
            PROFILE_FIELDS,
            DealBreaker,
        )
        app.run()
    finally:
        try:
            if key_pool is not None:
                key_pool.close()
        finally:
            pool.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProgram closed.")
    except Exception:
        logger.exception("Application startup/session failed")
        print("Could not run the application. Check configuration and logs.")
