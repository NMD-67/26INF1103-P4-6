import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from Data_Manager.database.database_connection import DatabaseConnection
from Data_Manager.repositories.matches_repo import MatchesRepo
from Data_Manager.repositories.user_repo import UserRepo
from Data_Manager.repository_user_source import RepositoryUserSource
from AI_Manager.Profile_Matching.matching_service import MatchingService
from Logic_Manager.Matching.score_calculator import ScoreCalculator
from Logic_Manager.services.match_service import MatchService
from AI_Manager.Profile_Matching.groq_key_pool import GroqKeyPool
from AI_Manager.Profile_Matching.groq_scorer import GroqScorer
from .goals_validator import GoalsValidator
from .interests_validator import InterestsValidator
from .mbti_validator import MbtiTableValidator
from .review_service import ReviewService
from .sentence_similarity import SentenceSimilarity

logger = logging.getLogger(__name__)

USER_ID = "2605776"   # pick a user who still has undecided candidates
LIMIT = 5
DRY_RUN = True        # True: log what would change, but don't change any score
SAVE = False          # False: print only, write nothing to the database

if __name__ == "__main__":
    keys = GroqKeyPool.from_env()
    pool = DatabaseConnection().create_pool()
    try:
        try:
            similarity = SentenceSimilarity.from_env()
            reviewer = ReviewService(
                [InterestsValidator(similarity), MbtiTableValidator(), GoalsValidator(similarity)],
                tolerance=25, dry_run=DRY_RUN)
        except RuntimeError:
            logger.warning("Hugging Face unavailable; running without review checks")
            reviewer = None

        source = RepositoryUserSource(UserRepo(pool))
        service = MatchingService(
            GroqScorer(keys),
            source,
            MatchService(MatchesRepo(pool), source),
            ScoreCalculator(),
            reviewer,
        )
        results = service.recommend(USER_ID, limit=LIMIT)
        for cid, r in results.items():
            c = r.categories
            print(cid, "overall:", r.overall,
                  "| interests:", c.interests_lifestyle,
                  "| personality:", c.personality_values,
                  "| goals:", c.relationship_goals,
                  "|", r.reason)
        if SAVE:
            print(service.save(USER_ID, results))
    finally:
        keys.close()
        pool.close()