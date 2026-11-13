# Owns one Groq client per API key and switches to the next key when one is rate-limited or rejected.

import os
import logging

from groq import Groq

logger = logging.getLogger(__name__)


class GroqKeyPool:
    def __init__(self, api_keys, timeout=30.0):
        keys = [k.strip() for k in api_keys if k and k.strip()]
        if not keys:
            raise RuntimeError("No Groq API keys supplied.")
        self._clients = [Groq(api_key=k, timeout=timeout) for k in keys]
        self._index = 0

    @classmethod
    def from_env(cls):
        names = os.getenv("GROQ_KEY_NAMES")
        if names:
            keys = [os.getenv(n.strip()) for n in names.split(",")]
            missing = [n.strip() for n, k in zip(names.split(","), keys) if not k]
            if missing:
                logger.warning("No value set for: %s", ", ".join(missing))
        else:
            keys = [os.getenv("PROFILE_MATCHING_API_KEY") or os.getenv("GROQ_API_KEY")]
        return cls(keys)

    @property
    def client(self):
        return self._clients[self._index] if self._index < len(self._clients) else None

    def rotate(self) -> bool:
        self._index += 1
        if self._index < len(self._clients):
            logger.warning("Switched to Groq key %d of %d", self._index + 1, len(self._clients))
            return True
        logger.error("All %d Groq keys are exhausted", len(self._clients))
        return False

    def close(self):
        for c in self._clients:
            c.close()