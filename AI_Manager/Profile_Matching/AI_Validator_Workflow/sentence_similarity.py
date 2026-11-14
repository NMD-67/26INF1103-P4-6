"""Local semantic similarity for interests: no hosted inference or API tokens.

Install: pip install sentence-transformers
The model must already be cached locally. Optionally set
LOCAL_EMBEDDING_MODEL to a previously downloaded model directory.
"""
import os

# Prevent Hugging Face Hub from making metadata/network requests.
# Set before importing sentence_transformers/huggingface_hub.
os.environ["HF_HUB_OFFLINE"] = "1"


class SentenceSimilarity:
    """Compare one text against many using normalized local embeddings.

    Scores are heuristic similarity indices, NOT validated compatibility odds.
    """

    def __init__(self, model=None, low=0.1, high=0.7, batch_size=50):
        if high <= low:
            raise ValueError("high must be greater than low")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "Local embeddings require: pip install sentence-transformers"
            ) from exc
        path = model or os.getenv("LOCAL_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        try:
            self._model = SentenceTransformer(path, local_files_only=True)
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                "Embedding model not available locally. Run the previous online "
                "version once to cache it, or set LOCAL_EMBEDDING_MODEL to "
                "a downloaded model folder."
            ) from exc
        self._low, self._high = float(low), float(high)
        self._batch_size = batch_size

    @classmethod
    def from_env(cls):
        """Compatibility with the previous call site; requires no API keys."""
        return cls()

    def compare(self, text_a: str, text_b: str) -> int | None:
        return self.compare_many(text_a, [text_b])[0]

    def compare_many(self, source: str, texts: list[str]) -> list[int | None]:
        result = [None] * len(texts)
        if not source or not source.strip():
            return result
        valid = [i for i, t in enumerate(texts) if t and t.strip()]
        if not valid:
            return result
        inputs = [source] + [texts[i] for i in valid]
        vectors = self._model.encode(inputs, batch_size=self._batch_size,
                                     normalize_embeddings=True)
        # Dot product of unit vectors = cosine similarity; no numpy import needed.
        for idx, vector in zip(valid, vectors[1:]):
            similarity = sum(float(a) * float(b) for a, b in zip(vectors[0], vector))
            result[idx] = self._scale(similarity)
        return result

    def _scale(self, similarity: float) -> int:
        fraction = (similarity - self._low) / (self._high - self._low)
        return round(100 * max(0.0, min(1.0, fraction)))

    def close(self):
        pass
