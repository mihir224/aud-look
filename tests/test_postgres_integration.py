import json
from uuid import uuid4

import pytest
from psycopg.rows import dict_row

from app.db import get_connection
from app.ingestion.pipeline import clear_indexed_content, upsert_audio
from app.retrieval.lexical import lexical_search


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
                clear_indexed_content(connection, first_id)
                cursor.execute("SELECT count(*) FROM utterances WHERE audio_id = %s", (first_id,))
                assert cursor.fetchone()["count"] == 0
                cursor.execute("SELECT count(*) FROM semantic_chunks WHERE audio_id = %s", (first_id,))
                assert cursor.fetchone()["count"] == 0
        finally:
            connection.rollback()
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM audio_files WHERE slug = %s", (slug,))
            connection.commit()


@pytest.mark.integration
def test_lexical_search_uses_entity_aliases_without_rewriting_evidence():
    slug = f"entity-alias-{uuid4()}"
    episode = {
        "slug": slug,
        "filename": "entity-alias.mp3",
        "title": "Entity Alias Fixture",
        "guest": "Geoffrey Kent",
        "source_url": "https://example.invalid/entity-alias",
        "duration_ms": 10_000,
        "sha256": uuid4().hex * 2,
        "tags": ["fixture"],
        "expected_speakers": 2,
    }
    with get_connection() as connection, connection.cursor(row_factory=dict_row) as cursor:
        audio_id = upsert_audio(connection, episode)
        cursor.execute(
            """
            INSERT INTO utterances (audio_id, sequence_no, speaker, start_ms, end_ms, text, normalized_text)
            VALUES (%s, 1, 'spk:1', 100, 1000, 'Jeffrey Kent trusts instinct.', 'jeffrey kent trusts instinct')
            RETURNING id, text
            """,
            (audio_id,),
        )
        utterance = cursor.fetchone()
        connection.commit()

    try:
        results = lexical_search("Geoffrey Kent", limit=20)
        assert any(candidate.utterance_id == utterance["id"] for candidate in results)
        assert utterance["text"] == "Jeffrey Kent trusts instinct."
    finally:
        with get_connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM audio_files WHERE slug = %s", (slug,))
            connection.commit()
