import logging
from dataclasses import replace, fields
from math import isfinite
from models.category_scores import CategoryScores

logger = logging.getLogger(__name__)


class ReviewService:
    """Keep valid AI scores within the configured tolerance of independent checks."""

    def __init__(self, validators, tolerance=25, dry_run=False):
        if not self._valid_number(tolerance) or tolerance < 0:
            raise ValueError("Tolerance must be a finite non-negative number")
        self._validators = list(validators)
        self._tolerance = tolerance
        self._dry_run = dry_run

    @staticmethod
    def _valid_number(value):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value)

    @classmethod
    def validate_scores(cls, scores, count):
        if len(scores) != count:
            raise ValueError("Reviewer result count does not match candidates")
        for score in scores:
            if not isinstance(score, CategoryScores):
                raise ValueError("Expected category scores")
            for field in fields(CategoryScores):
                value = getattr(score, field.name)
                if not cls._valid_number(value) or not 0 <= value <= 100:
                    raise ValueError("Category scores must be finite numbers from 0 to 100")

    def correct(self, main, candidates, scores):
        self.validate_scores(scores, len(candidates))
        out = list(scores)
        categories = {field.name for field in fields(CategoryScores)}
        for validator in self._validators:
            try:
                category = validator.category
                if category not in categories:
                    raise ValueError("Unknown validator category")
                checks = list(validator.validate_batch(main, candidates))
                if len(checks) != len(candidates):
                    raise ValueError("Validator result count does not match candidates")
                for check in checks:
                    if check is not None and (not self._valid_number(check) or not 0 <= check <= 100):
                        raise ValueError("Validator scores must be between 0 and 100 or None")
                updated = list(out)
                for i, check in enumerate(checks):
                    if check is None:
                        continue
                    ai = getattr(out[i], category)
                    fixed = min(max(ai, check - self._tolerance), check + self._tolerance)
                    if fixed != ai:
                        logger.info("%s: AI %s, check %s -> %s (dry run: %s)",
                                    category, ai, check, fixed, self._dry_run)
                        if not self._dry_run:
                            updated[i] = replace(out[i], **{category: fixed})
                self.validate_scores(updated, len(candidates))
                out = updated
            except Exception:
                logger.exception("Invalid reviewer output; keeping previous valid scores")
        return out
