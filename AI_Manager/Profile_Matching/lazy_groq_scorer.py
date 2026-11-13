"""Create scoring clients on first use rather than during application startup."""
import logging
from .compatibility_scorer import CompatibilityScorer
from .groq_key_pool import GroqKeyPool
from .groq_scorer import GroqScorer

logger = logging.getLogger(__name__)


class LazyGroqScorer(CompatibilityScorer):
    def __init__(self):
        self._pool = None
        self._scorer = None

    def prepare(self) -> bool:
        if self._scorer is not None:
            return True
        try:
            self._pool = GroqKeyPool.from_env()
            self._scorer = GroqScorer(self._pool)
            return True
        except Exception:
            logger.exception("Could not initialise AI scoring; other menu options remain available")
            self.close()
            return False

    def score(self, main_user, candidate):
        if not self.prepare():
            return None
        return self._scorer.score(main_user, candidate)

    def close(self):
        try:
            if self._pool is not None:
                self._pool.close()
        except Exception:
            logger.exception("Could not close scoring clients")
        finally:
            self._pool = None
            self._scorer = None
