from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.config import get_settings


QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


class Embedder:
    def __init__(self) -> None:
        settings = get_settings()
        self.model_name = settings.embedding_model
        self.model = SentenceTransformer(self.model_name, device=settings.model_device)

    def encode_passages(self, passages: list[str]) -> list[list[float]]:
        vectors = self.model.encode(passages, normalize_embeddings=True, show_progress_bar=False)
        result = vectors.tolist()
        if any(len(vector) != 768 for vector in result):
            raise ValueError("Expected 768-dimensional BGE embeddings")
        return result

    def encode_query(self, query: str) -> list[float]:
        return self.encode_passages([QUERY_PREFIX + query])[0]


@lru_cache
def get_embedder() -> Embedder:
    return Embedder()

