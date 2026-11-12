"""
AI Manager: scores compatibility between two User objects.

Pipeline per pair:
    User, User -> PromptBuilder -> AIClient -> ResponseParser -> ResponseValidator -> Match
"""

import json
import logging
import math
import os
import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

import groq
from groq import Groq

from models import User

logger = logging.getLogger(__name__)


# ======================================================================
# Exceptions (these feed the exception-handling matrix)
# ======================================================================
class AIError(Exception):
    """Base class for all AI Manager errors."""


class AIPermanentError(AIError):
    """Retrying cannot help (bad key, bad request, wrong input type)."""


class AIRetryableError(AIError):
    """Transient problem; worth retrying."""


class AIConnectionError(AIRetryableError):
    """Timeout, rate limit, 5xx, network failure."""


class AIResponseError(AIRetryableError):
    """Empty, truncated or otherwise unusable response."""


class AIParseError(AIResponseError):
    """Response is not valid JSON / not a JSON object."""


class AISchemaError(AIResponseError):
    """JSON is valid but fields are missing, wrong type or out of range."""


# ======================================================================
# AI client: interface -> abstract base -> concrete implementations
# ======================================================================
class AIClient(ABC):
    """Interface: anything that can turn (system, user) prompts into raw text."""

    @abstractmethod
    def complete(self, system: str, user: str) -> str: ...

    def close(self) -> None:
        pass


class BaseAIClient(AIClient):
    """Abstract base: shared empty-response check; subclasses implement _send()."""

    def complete(self, system: str, user: str) -> str:
        raw = self._send(system, user)
        if not isinstance(raw, str) or not raw.strip():
            raise AIResponseError("Response content was empty")
        return raw.strip()

    @abstractmethod
    def _send(self, system: str, user: str) -> str: ...


class GroqAIClient(BaseAIClient):
    _PERMANENT = (
        groq.AuthenticationError,
        groq.PermissionDeniedError,
        groq.BadRequestError,
        groq.NotFoundError,
        groq.UnprocessableEntityError,
    )
    _TRANSIENT = (
        groq.APIConnectionError,
        groq.APITimeoutError,
        groq.RateLimitError,
        groq.InternalServerError,
    )

    def __init__(self, model: str = "openai/gpt-oss-20b", timeout: float = 30.0):
        key = os.getenv("PROFILE_MATCHING_API_KEY") or os.getenv("GROQ_API_KEY")
        if not key or not key.strip():
            raise AIPermanentError(
                "Missing Groq API key. Set PROFILE_MATCHING_API_KEY or GROQ_API_KEY."
            )
        self._model = model
        self.__client = Groq(api_key=key.strip(), timeout=timeout)  # private

    def _send(self, system: str, user: str) -> str:
        try:
            resp = self.__client.chat.completions.create(
                model=self._model,
                max_completion_tokens=1024,
                reasoning_effort="low",
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except self._PERMANENT as e:
            raise AIPermanentError(f"{type(e).__name__}: {e}") from e
        except self._TRANSIENT as e:
            raise AIConnectionError(f"{type(e).__name__}: {e}") from e
        except groq.APIStatusError as e:
            raise AIPermanentError(f"API status {getattr(e, 'status_code', '?')}: {e}") from e
        except groq.GroqError as e:
            raise AIPermanentError(f"{type(e).__name__}: {e}") from e

        if not resp.choices:
            raise AIResponseError("Response contained no choices")
        choice = resp.choices[0]
        if getattr(choice, "finish_reason", None) == "length":
            raise AIResponseError("Response truncated (hit token limit)")
        return choice.message.content

    def close(self) -> None:
        self.__client.close()


class MockAIClient(AIClient):
    """For tests. Pass strings (returned) or Exceptions (raised), in order.
    The last item repeats once the queue is down to one."""

    def __init__(self, *responses):
        self._queue = list(responses)
        self.calls = 0

    def complete(self, system: str, user: str) -> str:
        self.calls += 1
        item = self._queue.pop(0) if len(self._queue) > 1 else self._queue[0]
        if isinstance(item, Exception):
            raise item
        return item


# ======================================================================
# User -> AI-facing data
# ======================================================================
class UserSerializer:
    """Selects the fields the AI is allowed to see from a User."""

    def serialize(self, user: User) -> dict:
        if not isinstance(user, User):
            raise AIPermanentError(f"Expected User, got {type(user).__name__}")
        return {
            "horoscope": getattr(user, "horoscope", None) or "",
            "mbti": user.mbti or "",
            "bio": user.bio or "",
            "expectations": user.expectations or "",
            "ccas": list(user.ccas or []),
            "events": list(user.events or []),
            "hobbies": list(user.hobbies or []),
            "interest_groups": list(user.interest_groups or []),
        }


# ======================================================================
# Prompt / parse / validate (one job each)
# ======================================================================
class PromptBuilder:
    SYSTEM = (
        "You compare two student profiles and return a single compatibility "
        "score from 0 to 100, plus a short reason (one or two sentences) "
        "explaining the score. Consider horoscope, MBTI, bio, expectations, "
        "CCAs, events, hobbies and interest groups. "
        "Respond ONLY with valid JSON in this exact format, no other text: "
        '{"score": <number 0-100>, "reason": "<short explanation>"}'
    )

    def __init__(self):
        self._serializer = UserSerializer()  # composition

    def build(self, a: User, b: User) -> tuple[str, str]:
        payload = {
            "profile_a": self._serializer.serialize(a),
            "profile_b": self._serializer.serialize(b),
        }
        return self.SYSTEM, json.dumps(payload, default=str)


class ResponseParser:
    def parse(self, raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise AIParseError(f"Response was not valid JSON: {e}") from e
        if not isinstance(data, dict):
            raise AIParseError(f"Expected a JSON object, got {type(data).__name__}")
        return data


@dataclass(frozen=True)
class AIScore:
    """Validated AI output for one pair (internal to the AI Manager)."""
    score: float
    reason: str


@dataclass(frozen=True)
class Match:
    """The result returned by the AI Manager for one pair of users.
    Refers to users by student_id only (association, no ownership)."""
    student_id: str            # the user being matched
    matched_user: str          # student_id of the candidate
    compatibility_score: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


class ResponseValidator:
    MAX_REASON_LENGTH = 300

    def validate(self, data: dict) -> AIScore:
        if "score" not in data:
            raise AISchemaError("JSON missing 'score' key")
        if "reason" not in data:
            raise AISchemaError("JSON missing 'reason' key")

        score = data["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            raise AISchemaError(f"Score is not a number: {score!r}")
        if isinstance(score, float) and not math.isfinite(score):
            raise AISchemaError(f"Score is not finite: {score!r}")
        if not 0 <= score <= 100:
            raise AISchemaError(f"Score out of range: {score}")

        reason = data["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise AISchemaError(f"Reason is missing or not text: {reason!r}")

        return AIScore(float(score), reason.strip()[: self.MAX_REASON_LENGTH])


class RetryPolicy:
    """Retries AIRetryableError with 1s, 2s, ... backoff. Never retries others."""

    def __init__(self, max_attempts: int = 3, sleep=time.sleep):
        self._max_attempts = max_attempts
        self._sleep = sleep  # injectable so tests don't wait

    def run(self, fn):
        for attempt in range(1, self._max_attempts + 1):
            try:
                return fn()
            except AIRetryableError as e:
                logger.warning("Attempt %d/%d failed: %s", attempt, self._max_attempts, e)
                if attempt == self._max_attempts:
                    raise
                self._sleep(2 ** (attempt - 1))


# ======================================================================
# The manager
# ======================================================================
class AIManager:
    def __init__(self, client: AIClient, retry: RetryPolicy | None = None):
        self._client = client                 # aggregation (injected, swappable)
        self._prompts = PromptBuilder()       # composition
        self._parser = ResponseParser()       # composition
        self._validator = ResponseValidator() # composition
        self._retry = retry or RetryPolicy()  # composition

    def match_pair(self, main: User, candidate: User) -> Match:
        """Returns a Match for one pair. Raises AIError if it cannot be scored."""
        system, user = self._prompts.build(main, candidate)  # bad input fails fast

        def attempt() -> AIScore:
            raw = self._client.complete(system, user)
            return self._validator.validate(self._parser.parse(raw))

        ai_score = self._retry.run(attempt)
        return Match(
            student_id=main.student_id,
            matched_user=candidate.student_id,
            compatibility_score=ai_score.score,
            reason=ai_score.reason,
        )

    def match_candidates(self, main: User, candidates: list[User]) -> list[Match]:
        """Returns Matches for every candidate that could be scored, highest score first.
        A failing candidate is skipped and logged. Raises AIPermanentError
        (e.g. bad API key) because every candidate would fail."""
        matches: list[Match] = []
        for candidate in candidates:
            try:
                matches.append(self.match_pair(main, candidate))
            except AIPermanentError:
                raise
            except AIError as e:
                logger.warning("Skipped candidate %s: %s", candidate.student_id, e)
        matches.sort(key=lambda m: m.compatibility_score, reverse=True)
        return matches


# ======================================================================
# Usage
# ======================================================================
# client = GroqAIClient()
# try:
#     manager = AIManager(client)
#     matches = manager.match_candidates(main_user, candidate_users)
# finally:
#     client.close()
#
# rows = [m.to_dict() for m in matches]   # hand to the Data Manager