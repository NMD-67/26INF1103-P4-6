
"""Configure services and start SITogether."""

import logging
from pathlib import Path

from dotenv import load_dotenv
from sitogether_app import SITogetherApp

load_dotenv(Path(__file__).resolve().parent / ".env")
logger = logging.getLogger(__name__)


def main():
    # Import inside the startup boundary so configuration/import failures are logged.
    from Data_Manager.database.database_connection import DatabaseConnection
    from Data_Manager.repositories.user_repo import UserRepo
    from Data_Manager.repositories.otp_repo import OTPRepo
    from Data_Manager.repositories.matches_repo import MatchesRepo
    from Logic_Manager.services.user_service import UserService
    from Logic_Manager.services.otp_service import OTPService
    from Logic_Manager.services.match_service import MatchService
    from models.dealbreaker import DealBreaker
    from config.user_fields import USER_FIELD_CONFIG, PROFILE_FIELDS
    from IO_Manager.console_io import ConsoleIO
    from Logic_Manager.profile_logic_manager import ProfileLogicManager
    from AI_Manager.Profile_Matching.lazy_groq_scorer import LazyGroqScorer
    from AI_Manager.Suggestions_generator import SuggestionsGenerator
    from Logic_Manager.services.connection_suggestion_service import ConnectionSuggestionService

    pool = DatabaseConnection().create_pool()
    scoring = None
    suggestions_generator = None
    try:
        users = UserService(UserRepo(pool))
        matches = MatchService(MatchesRepo(pool))
        otp = OTPService(OTPRepo(pool))
        scoring = LazyGroqScorer()
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
            if suggestions_generator is not None:
                suggestions_generator.close()
        finally:
            try:
                if scoring is not None:
                    scoring.close()
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
