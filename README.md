# aud-look

Local hybrid retrieval over six two-speaker podcast clips. Gemini is used only for the allowed hosted transcription step; embeddings, pgvector search, full-text search, and reranking run locally.

## Quick start

1. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.
2. Start the database: `make db-up`.
3. Apply the schema: `make migrate`.
4. Transcribe and cache the six bundled clips: `make transcribe`.
5. Generate local embeddings and indexes: `make ingest`.
6. Start the API and demo UI: `make up`.

Open `http://localhost:8501` for the Streamlit demo. The API is documented at `http://localhost:8000/docs`.

The first ingestion downloads the BGE embedding model. Re-running transcription reuses `dataset/transcripts/<episode>.json` when the source audio hash and transcription configuration match.
The Make targets rebuild the API image when dependencies or source change, so the pinned Gemini SDK stays in sync with the transcription adapter.

## Search API

```bash
curl 'http://localhost:8000/api/v1/search?q=money%20as%20freedom&k=5&strategy=hybrid'
```

Strategies are `lexical`, `semantic`, `rrf`, `hybrid`, and `hybrid_alt`. The default `hybrid` strategy unions lexical and semantic candidates, then reranks each result utterance directly. `hybrid_alt` selectively gives a response its preceding question as reranking context; it never gives a question its following answer.

## Evaluation

The repository includes 36 user-reviewed, timestamp-grounded queries in `eval/queries.yaml`: six per episode, with 24 `dev` and 12 `holdout`. Every label uses an episode slug and timestamp span rather than a mutable database ID.

```yaml
- id: janice-semantic-01
  query: how does she decide which ideas deserve action
  category: semantic
  split: dev
  relevant_spans:
    - audio_slug: janice-bryant-howroyd
      start_ms: 123000
      end_ms: 136000
```

Run `make evaluate` to write an ablation report under `eval/reports/`. It reports Recall@1/3/5, HitRate@1/3/5, MRR, per-category Recall@5, and warm p50/p95 latency.

## Important limitations

- Timestamped diarization is limited by the transcription quality. The pipeline refuses any episode that does not end with two validated speaker labels.
- Gemini custom vocabulary cannot be combined with diarization and word timestamps, so difficult proper nouns require audit rather than silent biasing.
- Exact vector scans are intentional for this small corpus. The HNSW index is present for the production-scale architecture but is disabled by default for deterministic evaluation.
- The bundled audio must only be redistributed if you have the appropriate rights.

See [submission.md](docs/submission.md) for the complete hackathon write-up, [ai-usage.md](docs/ai-usage.md) for the ChatGPT and coding-agent disclosure, and [architecture.md](docs/architecture.md) and [runbook.md](docs/runbook.md) for technical details.
