import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID

import yaml
from psycopg.rows import dict_row

from app.config import get_settings
from app.db import get_connection, vector_literal
from app.ingestion.chunking import build_chunks
from app.ingestion.normalize import normalize_text, validate_words, words_to_utterances
from app.models.embedder import get_embedder
from app.schemas import Word
from app.transcription.gemini import CONFIG, MODEL, GeminiTranscriber, transcription_config_hash


def load_yaml(path: Path):
    with path.open() as handle:
        return yaml.safe_load(handle) or {}


def transcript_path(slug: str) -> Path:
    return get_settings().transcript_dir / f"{slug}.json"


def load_cached_words(episode: dict) -> list[Word] | None:
    path = transcript_path(episode["slug"])
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    expected_hash = transcription_config_hash(episode["sha256"])
    if data.get("config_hash") != expected_hash:
        return None
    return [Word(**word) for word in data["words"]]


def write_cached_words(episode: dict, words: list[Word]) -> None:
    path = transcript_path(episode["slug"])
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "audio_sha256": episode["sha256"],
        "model": MODEL,
        "config": CONFIG,
        "config_hash": transcription_config_hash(episode["sha256"]),
        "words": [word.__dict__ for word in words],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n")


def apply_aliases(slug: str, words: list[Word], aliases: dict) -> list[Word]:
    mapping = aliases.get(slug, {})
    return [Word(word.text, mapping.get(word.speaker, word.speaker), word.start_ms, word.end_ms) for word in words]


def assert_audio_hash(episode: dict) -> Path:
    settings = get_settings()
    path = settings.audio_dir / episode["filename"]
    if not path.exists():
        raise FileNotFoundError(f"Missing bundled audio file: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != episode["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {path.name}")
    return path


def transcribe_all(force: bool = False) -> None:
    settings = get_settings()
    manifest = load_yaml(settings.manifest_path)
    aliases = load_yaml(Path("dataset/speaker_aliases.yaml"))
    transcriber = None
    for episode in manifest["episodes"]:
        audio_path = assert_audio_hash(episode)
        words = None if force else load_cached_words(episode)
        if words is None:
            if transcriber is None:
                transcriber = GeminiTranscriber(settings)
            words = transcriber.transcribe(audio_path)
            # Cache Gemini's original speaker labels. Any reviewed aliasing is applied only
            # for validation and ingestion so the source artifact stays auditable.
            validate_words(apply_aliases(episode["slug"], words, aliases), episode["duration_ms"])
            write_cached_words(episode, words)
            print(f"Transcribed {episode['slug']} ({len(words)} words)")
        else:
            print(f"Reused cached transcript for {episode['slug']} ({len(words)} words)")


def upsert_audio(connection, episode: dict) -> UUID:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            INSERT INTO audio_files (slug, filename, title, guest, source_url, duration_ms, sha256, tags, expected_speakers,
                                     transcription_model, transcription_config_hash)
            VALUES (%(slug)s, %(filename)s, %(title)s, %(guest)s, %(source_url)s, %(duration_ms)s, %(sha256)s,
                    %(tags)s::jsonb, %(expected_speakers)s, %(model)s, %(config_hash)s)
            ON CONFLICT (slug) DO UPDATE SET filename = EXCLUDED.filename, title = EXCLUDED.title, guest = EXCLUDED.guest,
                source_url = EXCLUDED.source_url, duration_ms = EXCLUDED.duration_ms, sha256 = EXCLUDED.sha256,
                tags = EXCLUDED.tags, expected_speakers = EXCLUDED.expected_speakers,
                transcription_model = EXCLUDED.transcription_model,
                transcription_config_hash = EXCLUDED.transcription_config_hash, updated_at = now()
            RETURNING id
            """,
            {**episode, "tags": json.dumps(episode["tags"]), "model": MODEL, "config_hash": transcription_config_hash(episode["sha256"])},
        )
        return cursor.fetchone()["id"]


def clear_indexed_content(connection, audio_id: UUID) -> None:
    """Remove derived episode rows before rebuilding them."""
    with connection.cursor() as cursor:
        # Chunks reference utterances through chunk_utterances, but are not
        # themselves deleted when utterances are replaced.
        cursor.execute("DELETE FROM semantic_chunks WHERE audio_id = %s", (audio_id,))
        cursor.execute("DELETE FROM utterances WHERE audio_id = %s", (audio_id,))


def ingest_episode(episode: dict, aliases: dict) -> None:
    words = load_cached_words(episode)
    if words is None:
        raise FileNotFoundError(f"No valid cached transcript for {episode['slug']}; run transcribe first")
    words = apply_aliases(episode["slug"], words, aliases)
    validate_words(words, episode["duration_ms"])
    utterances = words_to_utterances(words)
    chunks = build_chunks(utterances)
    embeddings = get_embedder().encode_passages([chunk.text for chunk in chunks])

    with get_connection() as connection:
        audio_id = upsert_audio(connection, episode)
        clear_indexed_content(connection, audio_id)
        with connection.cursor(row_factory=dict_row) as cursor:
            utterance_ids: dict[int, int] = {}
            for utterance in utterances:
                cursor.execute(
                    """
                    INSERT INTO utterances (audio_id, sequence_no, speaker, start_ms, end_ms, text, normalized_text)
                    VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """,
                    (audio_id, utterance.sequence_no, utterance.speaker, utterance.start_ms, utterance.end_ms, utterance.text, normalize_text(utterance.text)),
                )
                utterance_ids[utterance.sequence_no] = cursor.fetchone()["id"]
            for chunk, embedding in zip(chunks, embeddings):
                cursor.execute(
                    """
                    INSERT INTO semantic_chunks (audio_id, start_ms, end_ms, text, embedding_model, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector) RETURNING id
                    """,
                    (audio_id, chunk.start_ms, chunk.end_ms, chunk.text, get_settings().embedding_model, vector_literal(embedding)),
                )
                chunk_id = cursor.fetchone()["id"]
                for position, sequence_no in enumerate(chunk.utterance_sequence_nos):
                    cursor.execute(
                        "INSERT INTO chunk_utterances (chunk_id, utterance_id, position) VALUES (%s, %s, %s)",
                        (chunk_id, utterance_ids[sequence_no], position),
                    )
        connection.commit()
    print(f"Ingested {episode['slug']}: {len(utterances)} utterances, {len(chunks)} chunks")


def ingest_all() -> None:
    settings = get_settings()
    manifest = load_yaml(settings.manifest_path)
    aliases = load_yaml(Path("dataset/speaker_aliases.yaml"))
    for episode in manifest["episodes"]:
        assert_audio_hash(episode)
        ingest_episode(episode, aliases)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["transcribe", "ingest", "all"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command in {"transcribe", "all"}:
        transcribe_all(force=args.force)
    if args.command in {"ingest", "all"}:
        ingest_all()


if __name__ == "__main__":
    main()
