import re
from dataclasses import dataclass, field


def canonical_query(query: str) -> str:
    return " ".join(query.strip().strip('"\'').lower().split())


def literal_pattern(query: str) -> str | None:
    normalized = canonical_query(query)
    if not normalized:
        return None
    if re.fullmatch(r"[\w]+", normalized, flags=re.UNICODE):
        return r"\m" + re.escape(normalized) + r"\M"
    return re.escape(normalized)


@dataclass
class Candidate:
    utterance_id: int
    lexical_rank: int | None = None
    lexical_score: float | None = None
    semantic_rank: int | None = None
    semantic_score: float | None = None
    literal_match: bool = False
    sources: set[str] = field(default_factory=set)

    def merge(self, other: "Candidate") -> None:
        self.sources.update(other.sources)
        self.literal_match = self.literal_match or other.literal_match
        if other.lexical_rank is not None and (self.lexical_rank is None or other.lexical_rank < self.lexical_rank):
            self.lexical_rank, self.lexical_score = other.lexical_rank, other.lexical_score
        if other.semantic_rank is not None and (self.semantic_rank is None or other.semantic_rank < self.semantic_rank):
            self.semantic_rank, self.semantic_score = other.semantic_rank, other.semantic_score


def deduplicate(candidates: list[Candidate]) -> dict[int, Candidate]:
    merged: dict[int, Candidate] = {}
    for candidate in candidates:
        if candidate.utterance_id not in merged:
            merged[candidate.utterance_id] = candidate
        else:
            merged[candidate.utterance_id].merge(candidate)
    return merged


def rrf_score(candidate: Candidate, k: int = 60) -> float:
    score = 0.0
    if candidate.lexical_rank is not None:
        score += 1 / (k + candidate.lexical_rank)
    if candidate.semantic_rank is not None:
        score += 1 / (k + candidate.semantic_rank)
    return score
