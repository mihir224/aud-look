from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class Word:
    text: str
    speaker: str
    start_ms: int
    end_ms: int


@dataclass(frozen=True)
class Utterance:
    sequence_no: int
    speaker: str
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class Chunk:
    start_ms: int
    end_ms: int
    text: str
    utterance_sequence_nos: list[int]


class EpisodeResponse(BaseModel):
    id: str
    slug: str
    title: str
    guest: str
    filename: str
    duration_ms: int
    utterance_count: int


class SearchResult(BaseModel):
    rank: int
    audio_id: str
    audio_slug: str
    title: str
    filename: str
    speaker: str
    speaker_name: str
    speaker_role: str
    start_ms: int
    end_ms: int
    text: str
    context_before: str | None = None
    context_after: str | None = None
    match_sources: list[str]
    literal_match: bool
    debug: dict[str, float | int | None] | None = None


class SearchResponse(BaseModel):
    query: str
    strategy: str
    results: list[SearchResult]
    elapsed_ms: float = Field(ge=0)
