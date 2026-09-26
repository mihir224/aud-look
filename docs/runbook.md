# Runbook

## First run

```bash
cp .env.example .env
# Add GEMINI_API_KEY to .env
make db-up
make migrate
make transcribe
make ingest
make up
```

`make transcribe` uploads one MP3 at a time, deletes the temporary remote file when possible, validates the diarization output, and writes canonical JSON under `dataset/transcripts/`. `make ingest` does not need the Gemini key when valid caches exist.

## Common failures

- **Missing key:** add `GEMINI_API_KEY` to `.env`; do not paste it into source code or a terminal transcript.
- **More/fewer than two speakers:** inspect the cached JSON, add a reviewed explicit mapping in `dataset/speaker_aliases.yaml`, and rerun ingestion. Do not guess speaker identities.
- **Model memory pressure:** keep `MODEL_DEVICE=cpu`, leave the UI calling the API rather than loading models itself, and reduce the reranker candidate cap only after measuring dev-set recall.
- **No search results:** verify `make migrate` and `make ingest` completed, then check `GET /healthz` and `GET /api/v1/episodes`.
- **Evaluation error:** verify the reviewed `eval/queries.yaml` is mounted in the API container and that ingestion completed before running `make evaluate`.
