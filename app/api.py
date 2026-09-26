from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row

from app.db import get_connection
from app.retrieval.hybrid import STRATEGIES, search
from app.schemas import EpisodeResponse, SearchResponse


app = FastAPI(title="aud-look", version="0.1.0")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    try:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as error:
        raise HTTPException(status_code=503, detail="Database unavailable") from error
    return {"status": "ok"}


@app.get("/api/v1/episodes", response_model=list[EpisodeResponse])
def episodes() -> list[EpisodeResponse]:
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT a.id, a.slug, a.title, a.guest, a.filename, a.duration_ms, count(u.id) AS utterance_count
            FROM audio_files a
            LEFT JOIN utterances u ON u.audio_id = a.id
            GROUP BY a.id
            ORDER BY a.title
            """
        )
        return [EpisodeResponse(**{**row, "id": str(row["id"])}) for row in cursor.fetchall()]


@app.get("/api/v1/search", response_model=SearchResponse)
def search_endpoint(
    q: str = Query(min_length=1, max_length=500),
    k: int = Query(default=5, ge=1, le=20),
    strategy: str = Query(default="hybrid"),
    debug: bool = False,
) -> SearchResponse:
    if strategy not in STRATEGIES:
        raise HTTPException(status_code=422, detail=f"strategy must be one of {sorted(STRATEGIES)}")
    try:
        return search(q, k=k, strategy=strategy, debug=debug)
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
