
"""Shared hybrid validator configuration."""

import logging

from .goals_validator import GoalsValidator
from .interests_validator import InterestsValidator
from .mbti_validator import MbtiTableValidator
from .review_service import ReviewService
from .sentence_similarity import SentenceSimilarity

logger = logging.getLogger(__name__)


def create_reviewer(tolerance=25, dry_run=False):
    validators = [
        MbtiTableValidator(),
        GoalsValidator()
    ]

    try:
        similarity = SentenceSimilarity.from_env()
        validators.insert(
            0, InterestsValidator(similarity)
        )

    except (RuntimeError, OSError) as exc:
        logger.warning(
            "Local interests model unavailable: %s",
            exc
        )

    return ReviewService(
        validators,
        tolerance=tolerance,
        dry_run=dry_run
    )
