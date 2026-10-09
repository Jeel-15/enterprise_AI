import numpy as np

from ai_platform.config import settings
from ai_platform.embeddings import dense_model


class SemanticCache:
    def __init__(self, threshold: float | None = None):
        self.threshold = threshold if threshold is not None else settings.cache_threshold
        self.vectors: list[np.ndarray] = []
        self.answers: list[str] = []

    def _embed(self, text: str) -> np.ndarray:
        v = np.array(next(iter(dense_model.embed([text]))))
        return v / np.linalg.norm(v)

    def get(self, query: str):
        if not self.vectors:
            return None
        sims = np.array(self.vectors) @ self._embed(query)
        i = int(sims.argmax())
        if sims[i] >= self.threshold:
            return self.answers[i], float(sims[i])
        return None

    def put(self, query: str, answer: str) -> None:
        self.vectors.append(self._embed(query))
        self.answers.append(answer)