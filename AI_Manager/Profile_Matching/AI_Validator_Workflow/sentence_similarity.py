import os
import logging

from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)
_SWAP_CODES = (401, 402, 403, 429)


class SentenceSimilarity:
    """Scores how alike two texts are (0-100). Owns one client per token (composition)."""

    def __init__(self, tokens, model="sentence-transformers/all-MiniLM-L6-v2",
                 low=0.1, high=0.7, timeout=20.0, batch_size=50):
        tokens = [t.strip() for t in tokens if t and t.strip()]
        if not tokens:
            raise RuntimeError("No Hugging Face tokens supplied.")
        self._clients = [InferenceClient(provider="auto", api_key=t, timeout=timeout)
                         for t in tokens]
        self._index = 0
        self._model = model
        self._low, self._high = low, high     # starting guesses: calibrate on real data
        self._batch_size = batch_size         # guess: lower it if the API rejects big lists

    @classmethod
    def from_env(cls):
        names = [n.strip() for n in os.getenv("HF_KEY_NAMES", "HF_TOKEN").split(",")]
        return cls([os.getenv(n) for n in names])

    def compare(self, text_a: str, text_b: str) -> int | None:
        return self.compare_many(text_a, [text_b])[0]

    def compare_many(self, source: str, texts: list[str]) -> list[int | None]:
        """One source text against many. One API call per batch_size texts."""
        results = [None] * len(texts)
        if not source.strip():
            return results
        todo = [i for i, t in enumerate(texts) if t.strip()]
        for s in range(0, len(todo), self._batch_size):
            chunk = todo[s:s + self._batch_size]
            sims = self._call(source, [texts[i] for i in chunk])
            if sims is None:
                break
            for i, sim in zip(chunk, sims):
                results[i] = self._scale(float(sim))
        return results

    def _call(self, source: str, texts: list[str]):
        while self._index < len(self._clients):
            try:
                return self._clients[self._index].sentence_similarity(
                    source, texts, model=self._model)
            except Exception as e:
                status = getattr(getattr(e, "response", None), "status_code", None)
                if status in _SWAP_CODES:
                    logger.warning("Hugging Face token %d unavailable (HTTP %s), swapping",
                                   self._index + 1, status)
                    self._index += 1
                    continue
                logger.exception("Similarity call failed")
                return None
        logger.error("All Hugging Face tokens exhausted")
        return None

    def _scale(self, sim: float) -> int:
        frac = (sim - self._low) / (self._high - self._low)
        return int(round(max(0.0, min(1.0, frac)) * 100))

    def close(self):
        pass   # InferenceClient holds no resources that need closing