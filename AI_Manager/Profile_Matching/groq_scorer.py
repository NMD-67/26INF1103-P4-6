# Concrete scorer that builds the prompt, calls the Groq API, then parses, validates, and retries the response.

import json
import math
import time
import logging

import groq

from models.user import User
from .compatibility_scorer import CompatibilityScorer
from .groq_key_pool import GroqKeyPool
from .score_result import ScoreResult
from models.category_scores import CategoryScores

logger = logging.getLogger(__name__)


class GroqScorer(CompatibilityScorer):
    FIELDS_FOR_AI = (
        "gender", "bio", "religion", "mbti", "match_preference",
        "here_for", "expectations", "ccas", "events", "hobbies", "interest_groups",
    )

    _INSTRUCTIONS = (
        "You compare two user dating/matching profiles (profile_a is the viewer, "
        "profile_b is the candidate). Return three category scores, each 0 to 100:\n"
        "- interests_lifestyle: based on hobbies, ccas, events, interest_groups, bio.\n"
        "- personality_values: based on mbti, bio, expectations, religion.\n"
        "- relationship_goals: based on here_for, match_preference, expectations "
        "(use gender to check whether match_preference fits).\n"
        "Also give one short reason (max 25 words) covering the main similarities or clashes. "
        "In the reason, never say 'profile A', 'profile B', 'A' or 'B'; say 'you' and 'they'. "
        "Respond ONLY with valid JSON: "
        '{"interests_lifestyle": <int>, "personality_values": <int>, '
        '"relationship_goals": <int>, "reason": "<text>"}'
    )

    _CATEGORY_KEYS = ("interests_lifestyle", "personality_values", "relationship_goals")

    def __init__(self, key_pool: GroqKeyPool, model="openai/gpt-oss-20b", max_attempts=3):
        self._pool = key_pool
        self._model = model
        self._max_attempts = max_attempts

    def score(self, main_user, candidate):
        if self._pool.client is None:
            logger.error("No Groq keys available")
            return None
        try:
            content = self._build_prompt(main_user, candidate)
        except Exception:
            logger.exception("Could not build prompt for %s", candidate.student_id)
            return None

        attempt = 1
        while attempt <= self._max_attempts:
            try:
                return self._parse_and_validate(self._call_api(content))
            except (groq.RateLimitError, groq.AuthenticationError) as e:
                logger.warning("Scoring key unavailable: %s", type(e).__name__)
                if self._pool.rotate():
                    continue
                return None
            except ValueError as e:
                logger.warning("Malformed response (%d/%d): %s", attempt, self._max_attempts, e)
            except (groq.PermissionDeniedError,
                    groq.BadRequestError, groq.NotFoundError,
                    groq.UnprocessableEntityError) as e:
                logger.error("Permanent API error: %s", e)
                return None
            except (groq.APIConnectionError, groq.APITimeoutError,
                    groq.InternalServerError) as e:
                logger.warning("Transient API error (%d/%d): %s", attempt, self._max_attempts, e)
            except (groq.APIStatusError, groq.GroqError):
                logger.exception("Groq error")
                return None
            except Exception:
                logger.exception("Unexpected error scoring %s", candidate.student_id)
                return None

            if attempt < self._max_attempts:
                time.sleep(2 ** (attempt - 1))
            attempt += 1

        logger.error("Giving up on %s", candidate.student_id)
        return None

    def _to_ai_dict(self, user: User) -> dict:
        details = user.get_user_details()
        return {f: details.get(f) if details.get(f) is not None else ""
                for f in self.FIELDS_FOR_AI}

    def _build_prompt(self, a: User, b: User) -> str:
        return json.dumps(
            {"profile_a": self._to_ai_dict(a), "profile_b": self._to_ai_dict(b)},
            default=str,
        )

    def _call_api(self, user_content: str) -> str:
        response = self._pool.client.chat.completions.create(
            model=self._model,
            max_completion_tokens=1024,
            reasoning_effort="low",
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": self._INSTRUCTIONS},
                {"role": "user", "content": user_content},
            ],
        )
        choices = getattr(response, "choices", None)
        if not choices:
            raise ValueError("Response contained no choices")
        choice = choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise ValueError("Response truncated")
        raw = getattr(getattr(choice, "message", None), "content", None)
        if not isinstance(raw, str) or not raw.strip():
            raise ValueError("Response content was empty")
        return raw

    @staticmethod
    def _check_score(value, name: str) -> int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} is not a number: {value!r}")
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"{name} is not finite: {value!r}")
        if not 0 <= value <= 100:
            raise ValueError(f"{name} out of range: {value}")
        return int(round(value))

    @staticmethod
    def _parse_and_validate(raw: str) -> ScoreResult:
        try:
            parsed = json.loads(raw.strip())
        except json.JSONDecodeError as e:
            raise ValueError(f"Not valid JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise ValueError("JSON must be an object")

        values = {}
        for key in GroqScorer._CATEGORY_KEYS:
            if key not in parsed:
                raise ValueError(f"JSON missing '{key}'")
            values[key] = GroqScorer._check_score(parsed[key], key)

        reason = parsed.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("Reason must be a non-empty string")
        return ScoreResult(categories=CategoryScores(**values), reason=reason)
