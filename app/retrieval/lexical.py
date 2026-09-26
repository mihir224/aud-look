from psycopg.rows import dict_row

from app.db import get_connection
from app.retrieval.common import Candidate, canonical_query, literal_pattern


def lexical_search(query: str, limit: int = 20) -> list[Candidate]:
    normalized = canonical_query(query)
    pattern = literal_pattern(query)
    if not normalized:
        return []
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            WITH query_terms AS (SELECT websearch_to_tsquery('english', %(query)s) AS tsq)
            SELECT u.id,
                   ts_rank_cd(u.search_vector, query_terms.tsq) AS lexical_score,
                   CASE WHEN %(pattern)s::text IS NOT NULL AND u.normalized_text ~ %(pattern)s THEN TRUE ELSE FALSE END AS literal_match
            FROM utterances u CROSS JOIN query_terms
            WHERE u.search_vector @@ query_terms.tsq
               OR (%(pattern)s::text IS NOT NULL AND u.normalized_text ~ %(pattern)s)
            ORDER BY literal_match DESC, lexical_score DESC NULLS LAST, u.id ASC
            LIMIT %(limit)s
            """,
            {"query": normalized, "pattern": pattern, "limit": limit},
        )
        rows = cursor.fetchall()
    return [
        Candidate(
            utterance_id=row["id"],
            lexical_rank=rank,
            lexical_score=float(row["lexical_score"] or 0),
            literal_match=bool(row["literal_match"]),
            sources={"lexical"},
        )
        for rank, row in enumerate(rows, start=1)
    ]

