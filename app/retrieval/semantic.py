from psycopg.rows import dict_row

from app.config import get_settings
from app.db import get_connection, vector_literal
from app.models.embedder import get_embedder
from app.retrieval.common import Candidate


def semantic_search(query: str, limit: int = 10) -> list[Candidate]:
    embedding = get_embedder().encode_query(query)
    settings = get_settings()
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        if settings.vector_search_mode == "exact":
            cursor.execute("SET LOCAL enable_indexscan = off")
            cursor.execute("SET LOCAL enable_bitmapscan = off")
        cursor.execute(
            """
            WITH nearest_chunks AS (
                SELECT id, 1 - (embedding <=> %(embedding)s::vector) AS similarity
                FROM semantic_chunks
                ORDER BY embedding <=> %(embedding)s::vector
                LIMIT %(limit)s
            )
            SELECT cu.utterance_id, nearest_chunks.similarity, nearest_chunks.id AS chunk_id
            FROM nearest_chunks
            JOIN chunk_utterances cu ON cu.chunk_id = nearest_chunks.id
            ORDER BY nearest_chunks.similarity DESC, nearest_chunks.id ASC, cu.position ASC
            """,
            {"embedding": vector_literal(embedding), "limit": limit},
        )
        rows = cursor.fetchall()

    candidates: dict[int, Candidate] = {}
    chunk_ranks: dict[int, int] = {}
    for row in rows:
        chunk_id = row["chunk_id"]
        if chunk_id not in chunk_ranks:
            chunk_ranks[chunk_id] = len(chunk_ranks) + 1
        candidate = Candidate(
            utterance_id=row["utterance_id"],
            semantic_rank=chunk_ranks[chunk_id],
            semantic_score=float(row["similarity"]),
            sources={"semantic"},
        )
        if candidate.utterance_id not in candidates:
            candidates[candidate.utterance_id] = candidate
        else:
            candidates[candidate.utterance_id].merge(candidate)
    return list(candidates.values())

