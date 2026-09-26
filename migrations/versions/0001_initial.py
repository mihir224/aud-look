"""Initial aud-look schema.

Revision ID: 0001_initial
Revises:
"""

from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute(
        """
        CREATE TABLE audio_files (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug TEXT NOT NULL UNIQUE,
            filename TEXT NOT NULL,
            title TEXT NOT NULL,
            guest TEXT NOT NULL,
            source_url TEXT NOT NULL,
            duration_ms BIGINT NOT NULL CHECK (duration_ms > 0),
            sha256 TEXT NOT NULL UNIQUE,
            tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            expected_speakers SMALLINT NOT NULL DEFAULT 2,
            transcription_model TEXT,
            transcription_config_hash TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE utterances (
            id BIGSERIAL PRIMARY KEY,
            audio_id UUID NOT NULL REFERENCES audio_files(id) ON DELETE CASCADE,
            sequence_no INTEGER NOT NULL CHECK (sequence_no > 0),
            speaker TEXT NOT NULL,
            start_ms BIGINT NOT NULL CHECK (start_ms >= 0),
            end_ms BIGINT NOT NULL CHECK (end_ms >= start_ms),
            text TEXT NOT NULL CHECK (length(trim(text)) > 0),
            normalized_text TEXT NOT NULL,
            search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', normalized_text)) STORED,
            UNIQUE (audio_id, sequence_no)
        )
        """
    )
    op.execute("CREATE INDEX idx_utterances_fts ON utterances USING GIN(search_vector)")
    op.execute("CREATE INDEX idx_utterances_audio_time ON utterances(audio_id, start_ms)")
    op.execute(
        """
        CREATE TABLE semantic_chunks (
            id BIGSERIAL PRIMARY KEY,
            audio_id UUID NOT NULL REFERENCES audio_files(id) ON DELETE CASCADE,
            start_ms BIGINT NOT NULL CHECK (start_ms >= 0),
            end_ms BIGINT NOT NULL CHECK (end_ms >= start_ms),
            text TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding VECTOR(768) NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_semantic_chunks_hnsw ON semantic_chunks USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        """
        CREATE TABLE chunk_utterances (
            chunk_id BIGINT NOT NULL REFERENCES semantic_chunks(id) ON DELETE CASCADE,
            utterance_id BIGINT NOT NULL REFERENCES utterances(id) ON DELETE CASCADE,
            position SMALLINT NOT NULL CHECK (position >= 0),
            PRIMARY KEY (chunk_id, utterance_id),
            UNIQUE (chunk_id, position)
        )
        """
    )
    op.execute("CREATE INDEX idx_chunk_utterances_utterance ON chunk_utterances(utterance_id)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chunk_utterances")
    op.execute("DROP TABLE IF EXISTS semantic_chunks")
    op.execute("DROP TABLE IF EXISTS utterances")
    op.execute("DROP TABLE IF EXISTS audio_files")
