import json
from uuid import uuid4

import pytest
from psycopg.rows import dict_row

from app.db import get_connection
from app.ingestion.pipeline import upsert_audio


@pytest.mark.integration
def test_schema_supports_idempotent_audio_upsert_fts_and_vectors():
    slug = f"integration-{uuid4()}"
    episode = {
        "slug": slug,
        "filename": "fixture.mp3",
        "title": "Fixture",
        "guest": "Fixture Guest",
        "source_url": "https://example.invalid/fixture",
        "duration_ms": 10_000,
        "sha256": uuid4().hex * 2,
        "tags": ["fixture"],
        "expected_speakers": 2,
    }
    vector = "[1," + ",".join("0" for _ in range(767)) + "]"
    with get_connection() as connection:
        try:
            first_id = upsert_audio(connection, episode)
            second_id = upsert_audio(connection, episode)
            assert first_id == second_id
            with connection.cursor(row_factory=dict_row) as cursor:
                cursor.execute(
                    """
                    INSERT INTO utterances (audio_id, sequence_no, speaker, start_ms, end_ms, text, normalized_text)
                    VALUES (%s, 1, 'spk_1', 100, 1000, 'Basecamp avoids VC money.', 'basecamp avoids vc money')
                    RETURNING id
                    """,
                    (first_id,),
                )
                utterance_id = cursor.fetchone()["id"]
                cursor.execute(
                    """
                    INSERT INTO semantic_chunks (audio_id, start_ms, end_ms, text, embedding_model, embedding)
                    VALUES (%s, 100, 1000, 'spk_1: Basecamp avoids VC money.', 'fixture', %s::vector)
                    RETURNING id
                    """,
                    (first_id, vector),
                )
                chunk_id = cursor.fetchone()["id"]
                cursor.execute("INSERT INTO chunk_utterances (chunk_id, utterance_id, position) VALUES (%s, %s, 0)", (chunk_id, utterance_id))
                cursor.execute("SELECT id FROM utterances WHERE search_vector @@ websearch_to_tsquery('english', 'Basecamp VC')")
                assert cursor.fetchone()["id"] == utterance_id
                cursor.execute("SELECT id FROM semantic_chunks ORDER BY embedding <=> %s::vector LIMIT 1", (vector,))
                assert cursor.fetchone()["id"] == chunk_id
        finally:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM audio_files WHERE slug = %s", (slug,))
            connection.commit()
