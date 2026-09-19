from typing import List


class MockEmbeddingProvider:
    def embed(self, texts: List[str]) -> List[List[float]]:
        # Deterministic, tiny embeddings: use length-based vectors
        return [[float(len(t) % 10) for _ in range(8)] for t in texts]
