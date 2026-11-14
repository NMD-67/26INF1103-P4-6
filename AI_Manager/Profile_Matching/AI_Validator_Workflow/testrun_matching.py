
"""Test validated matching and optional database saving."""

import os
import logging
from pathlib import Path

# =========================================
# ENVIRONMENT CONFIGURATION
# =========================================

# Disable tqdm progress bars
os.environ["TQDM_DISABLE"] = "1"

# Load environment variables
from dotenv import load_dotenv

load_dotenv(
    Path(__file__).resolve().parents[3] / ".env"
)

# =========================================
# LOGGING CONFIGURATION
# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)

# Hide unnecessary third-party logs
for library in [
    "httpx",
    "httpcore",
    "sentence_transformers",
    "transformers",
    "huggingface_hub",
]:
    logging.getLogger(library).setLevel(logging.WARNING)

# =========================================
# PROJECT IMPORTS
# =========================================

from Data_Manager.database.database_connection import DatabaseConnection
from Data_Manager.repositories.matches_repo import MatchesRepo
from Data_Manager.repositories.user_repo import UserRepo
from Data_Manager.repository_user_source import RepositoryUserSource

from Logic_Manager.Matching.matching_service import MatchingService
from Logic_Manager.Matching.score_calculator import ScoreCalculator
from Logic_Manager.services.match_service import MatchService

from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
from AI_Manager.Profile_Matching.groq_scorer import GroqScorer

from .reviewer_factory import create_reviewer

logger = logging.getLogger(__name__)

# Configuration
USER_ID = "2302259"
LIMIT = 5

DRY_RUN = False
SAVE = True

VALIDATION_TOLERANCE = 25


def display_results(results):
    print("\n=== FINAL MATCHING RESULTS ===")

    for candidate_id, result in results.items():
        categories = result.categories

        print(f"\nCandidate: {candidate_id}")
        print(f"Overall: {result.overall}")
        print(
            f"Interests: "
            f"{categories.interests_lifestyle}"
        )
        print(
            f"Personality: "
            f"{categories.personality_values}"
        )
        print(
            f"Goals: "
            f"{categories.relationship_goals}"
        )
        print(f"Reason: {result.reason}")


def main():
    if SAVE and DRY_RUN:
        raise ValueError(
            "Set DRY_RUN=False before saving results."
        )

    keys = None
    pool = None

    try:
        keys = GroqKeyPool.from_env()
        pool = DatabaseConnection().create_pool()

        source = RepositoryUserSource(UserRepo(pool))

        match_service = MatchService(
            MatchesRepo(pool),
            source
        )

        reviewer = create_reviewer(
            tolerance=VALIDATION_TOLERANCE,
            dry_run=DRY_RUN
        )

        service = MatchingService(
            GroqScorer(keys),
            source,
            match_service,
            ScoreCalculator(),
            reviewer
        )

        logger.info("Starting profile matching")

        results = service.recommend(
            USER_ID,
            limit=LIMIT
        )

        if not results:
            logger.warning("No candidates returned")
            return

        display_results(results)

        if SAVE:
            logger.info("Saving results to database")

            counts = service.save(USER_ID, results)

            logger.info("Save summary: %s", counts)

            if counts["not_saved"] or counts["failed"]:
                logger.warning(
                    "Some results were not saved."
                )
        else:
            logger.info(
                "SAVE=False: no database writes"
            )

    except Exception:
        logger.exception("Matching workflow failed")
        raise

    finally:
        if keys is not None:
            keys.close()

        if pool is not None:
            pool.close()

        logger.info("Resources closed")


if __name__ == "__main__":
    main()
