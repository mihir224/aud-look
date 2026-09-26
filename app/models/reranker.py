from functools import lru_cache

from sentence_transformers import CrossEncoder

from app.config import get_settings


class Reranker:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = CrossEncoder(settings.reranker_model, device=settings.model_device, max_length=512)

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        return [float(score) for score in self.model.predict([(query, passage) for passage in passages], batch_size=16)]


@lru_cache
def get_reranker() -> Reranker:
    return Reranker()

