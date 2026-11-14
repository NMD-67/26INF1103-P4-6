import logging
from dataclasses import replace

from models.user import User
from models.category_scores import CategoryScores
from .category_validator import CategoryValidator

logger = logging.getLogger(__name__)


class ReviewService:
    """Guards AI output: pulls any category score that strays too far from its
    independent check back to within `tolerance`. Stores nothing."""

    def __init__(self, validators: list[CategoryValidator], tolerance: int = 25,
                 dry_run: bool = False):
        self._validators = list(validators)    # polymorphic: any CategoryValidator
        self._tolerance = tolerance
        self._dry_run = dry_run                # True = only log, don't change scores

    def correct(self, main: User, candidates: list[User],
                scores: list[CategoryScores]) -> list[CategoryScores]:
        out = list(scores)
        for v in self._validators:
            try:
                checks = v.validate_batch(main, candidates)
            except Exception:
                logger.exception("Validator %s crashed; keeping AI scores", v.category)
                continue
            for i, check in enumerate(checks):
                if check is None:
                    continue
                ai = getattr(out[i], v.category)
                fixed = min(max(ai, check - self._tolerance), check + self._tolerance)
                if fixed == ai:
                    continue
                logger.info("%s for %s: AI %d, check %d -> %d%s", v.category,
                            candidates[i].student_id, ai, check, fixed,
                            " (dry run)" if self._dry_run else "")
                if not self._dry_run:
                    out[i] = replace(out[i], **{v.category: fixed})
        return out