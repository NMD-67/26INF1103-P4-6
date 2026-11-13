# Runner script that wires the objects together and executes one matching run (contains no classes).

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from Data_Manager.database.connection import create_connection_pool
from repositories.matches_repo import MatchesRepo
from services.match_service import MatchService
from .groq_key_pool import GroqKeyPool
from .groq_scorer import GroqScorer
from .supabase_user_source import SupabaseUserSource
from .matching_service import MatchingService

if __name__ == "__main__":
    keys = GroqKeyPool.from_env()
    pool = create_connection_pool()
    try:
        service = MatchingService(
            GroqScorer(keys),
            SupabaseUserSource.from_env(),
            MatchService(MatchesRepo(pool)),
        )
        results = service.recommend("2603197", limit=5)
        for cid, r in results.items():
            print(cid, r.score, r.reason)
        print(service.save("2603197", results))
    finally:
        keys.close()
        pool.close()