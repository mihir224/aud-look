from concurrent.futures import ThreadPoolExecutor
import re
from time import perf_counter

from psycopg.rows import dict_row

from app.db import get_connection
from app.metadata import speaker_identity
from app.models.reranker import get_reranker
from app.retrieval.common import Candidate, canonical_query, deduplicate, literal_pattern, rrf_score
from app.retrieval.lexical import lexical_search
from app.retrieval.semantic import semantic_search
from app.schemas import SearchResponse, SearchResult


STRATEGIES = {"lexical", "semantic", "rrf", "hybrid", "hybrid_alt"}
EVALUATION_STRATEGIES = STRATEGIES
QA_PAIR_WEIGHT = 0.35
QUESTION_START = re.compile(r"^(?:who|what|when|where|why|how|which|whose|do|does|did|is|are|can|could|would|will|should)\b", re.IGNORECASE)


def _fetch_details(ids: list[int], query: str) -> dict[int, dict]:
    if not ids:
        return {}
    pattern = literal_pattern(query)
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            WITH all_utterances AS (
                SELECT u.id, u.audio_id, u.sequence_no, u.speaker, u.start_ms, u.end_ms, u.text, u.normalized_text,
                       lag(u.text) OVER (PARTITION BY u.audio_id ORDER BY u.sequence_no) AS context_before,
                       lag(u.speaker) OVER (PARTITION BY u.audio_id ORDER BY u.sequence_no) AS context_before_speaker,
                       lag(u.end_ms) OVER (PARTITION BY u.audio_id ORDER BY u.sequence_no) AS context_before_end_ms,
                       lead(u.text) OVER (PARTITION BY u.audio_id ORDER BY u.sequence_no) AS context_after
                FROM utterances u
            )
            SELECT all_utterances.*, a.slug AS audio_slug, a.title, a.filename,
                   CASE WHEN %(pattern)s::text IS NOT NULL AND normalized_text ~ %(pattern)s THEN TRUE ELSE FALSE END AS literal_match
            FROM all_utterances
            JOIN audio_files a ON a.id = all_utterances.audio_id
            WHERE all_utterances.id = ANY(%(ids)s)
            """,
            {"ids": ids, "pattern": pattern},
        )
        return {row["id"]: row for row in cursor.fetchall()}


def _target_passage(detail: dict) -> str:
    return f"TARGET ({detail['speaker']}): {detail['text']}"


def _is_strict_literal_query(query: str) -> bool:
    stripped = query.strip()
    if len(stripped) >= 2 and stripped[0] in {'"', "'"} and stripped[-1] == stripped[0]:
        return True
    return bool(re.fullmatch(r"[\w-]+", stripped, flags=re.UNICODE))


def _looks_like_question(text: str | None) -> bool:
    if not text:
        return False
    stripped = text.strip()
    return stripped.endswith("?") or bool(QUESTION_START.match(stripped))


def _answer_pair_passage(detail: dict) -> str | None:
    """Give a response its preceding question as context, never the reverse."""
    before = detail.get("context_before")
    before_speaker = detail.get("context_before_speaker")
    before_end_ms = detail.get("context_before_end_ms")
    if not before or not before_speaker or before_speaker == detail["speaker"]:
        return None
    if not _looks_like_question(before):
        return None
    if before_end_ms is None or detail["start_ms"] - before_end_ms > 7_000:
        return None
    return f"QUESTION ({before_speaker}): {before}\nANSWER ({detail['speaker']}): {detail['text']}"


def _result(candidate: Candidate, detail: dict, rank: int, debug: bool, extra_score: float | None = None) -> SearchResult:
    diagnostics = None
    if debug:
        diagnostics = {
            "lexical_rank": candidate.lexical_rank,
            "lexical_score": candidate.lexical_score,
            "semantic_rank": candidate.semantic_rank,
            "semantic_score": candidate.semantic_score,
            "final_score": extra_score,
        }
    identity = speaker_identity(detail["audio_slug"], detail["speaker"])
    return SearchResult(
        rank=rank,
        audio_id=str(detail["audio_id"]),
        audio_slug=detail["audio_slug"],
        title=detail["title"],
        filename=detail["filename"],
        speaker=detail["speaker"],
        speaker_name=identity["name"],
        speaker_role=identity["role"],
        start_ms=detail["start_ms"],
        end_ms=detail["end_ms"],
        text=detail["text"],
        context_before=detail["context_before"],
        context_after=detail["context_after"],
        match_sources=sorted(candidate.sources),
        literal_match=candidate.literal_match or bool(detail["literal_match"]),
        debug=diagnostics,
    )


def _sort_reranked(
    candidates: list[Candidate], scores: list[float], details: dict[int, dict], prioritize_literal: bool
) -> list[tuple[Candidate, float]]:
    for candidate in candidates:
        candidate.literal_match = candidate.literal_match or bool(details[candidate.utterance_id]["literal_match"])
    return sorted(
        zip(candidates, scores),
        key=lambda item: (
            not item[0].literal_match if prioritize_literal else False,
            -item[1],
            min(rank for rank in [item[0].lexical_rank, item[0].semantic_rank] if rank is not None),
            item[0].utterance_id,
        ),
    )


def _rerank_target_only(
    query: str, candidates: list[Candidate], details: dict[int, dict], prioritize_literal: bool
) -> list[tuple[Candidate, float]]:
    scores = get_reranker().score(query, [_target_passage(details[candidate.utterance_id]) for candidate in candidates])
    return _sort_reranked(candidates, scores, details, prioritize_literal)


def _rerank_qa_pairs(
    query: str, candidates: list[Candidate], details: dict[int, dict], prioritize_literal: bool
) -> list[tuple[Candidate, float]]:
    """Score direct relevance, then selectively boost answers paired with prior questions."""
    target_passages = [_target_passage(details[candidate.utterance_id]) for candidate in candidates]
    pairs = [
        (index, passage)
        for index, candidate in enumerate(candidates)
        if (passage := _answer_pair_passage(details[candidate.utterance_id])) is not None
    ]
    scores = get_reranker().score(query, target_passages + [passage for _, passage in pairs])
    final_scores = scores[: len(candidates)]
    for (index, _), pair_score in zip(pairs, scores[len(candidates) :]):
        final_scores[index] = (1 - QA_PAIR_WEIGHT) * final_scores[index] + QA_PAIR_WEIGHT * pair_score
    return _sort_reranked(candidates, final_scores, details, prioritize_literal)


def search(query: str, k: int = 5, strategy: str = "hybrid", debug: bool = False) -> SearchResponse:
    started = perf_counter()
    prioritize_literal = _is_strict_literal_query(query)
    query = canonical_query(query)
    if not query:
        return SearchResponse(query=query, strategy=strategy, results=[], elapsed_ms=0)
    if strategy not in EVALUATION_STRATEGIES:
        raise ValueError(f"Unknown strategy: {strategy}")

    if strategy == "lexical":
        lexical, semantic = lexical_search(query), []
    elif strategy == "semantic":
        lexical, semantic = [], semantic_search(query)
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            lexical_future = executor.submit(lexical_search, query)
            semantic_future = executor.submit(semantic_search, query)
            lexical = lexical_future.result()
            semantic = semantic_future.result()

    if strategy == "lexical":
        candidates = lexical
    elif strategy == "semantic":
        candidates = sorted(semantic, key=lambda candidate: (candidate.semantic_rank or 999, candidate.utterance_id))
    else:
        candidates = list(deduplicate(lexical + semantic).values())

    details = _fetch_details([candidate.utterance_id for candidate in candidates], query)
    candidates = [candidate for candidate in candidates if candidate.utterance_id in details]
    for candidate in candidates:
        candidate.literal_match = candidate.literal_match or bool(details[candidate.utterance_id]["literal_match"])

    if strategy == "rrf":
        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -rrf_score(candidate),
                not candidate.literal_match if prioritize_literal else False,
                candidate.utterance_id,
            ),
        )
        scored = [(candidate, rrf_score(candidate)) for candidate in ranked]
    elif strategy == "hybrid":
        scored = _rerank_target_only(query, candidates[:60], details, prioritize_literal)
    elif strategy == "hybrid_alt":
        scored = _rerank_qa_pairs(query, candidates[:60], details, prioritize_literal)
    else:
        scored = [(candidate, candidate.lexical_score if strategy == "lexical" else candidate.semantic_score) for candidate in candidates]

    results = [_result(candidate, details[candidate.utterance_id], rank, debug, score) for rank, (candidate, score) in enumerate(scored[:k], start=1)]
    return SearchResponse(query=query, strategy=strategy, results=results, elapsed_ms=(perf_counter() - started) * 1000)
