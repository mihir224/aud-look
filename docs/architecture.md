# Architecture Decision Record: aud-look

## Retrieval path

```text
MP3 → Gemini verbatim transcript (speaker + word timestamps)
    → speaker-attributed utterances → PostgreSQL FTS + exact literal candidates
    → overlapping conversational chunks → local BGE vectors → pgvector candidates
    → union/deduplicate → local cross-encoder over target utterances
    → episode, speaker, timestamp, utterance, and provenance
```

The retrieval unit and result unit deliberately differ. Chunks retain enough conversation for semantic recall and pronoun resolution; individual utterances retain the precise speaker and timestamp required by the product.

## Key decisions

- **Gemini 3.5 Transcribe:** hosted transcription is permitted. Verbatim mode, diarization, and word timestamps preserve searchable evidence. Cached canonical transcripts make later runs local and reproducible.
- **PostgreSQL FTS plus exact matching:** FTS supplies high-recall word candidates while an exact regex match protects names, acronyms, identifiers, and quoted phrases. Native FTS is not BM25; a production deployment may substitute OpenSearch/BM25 without changing the downstream contract.
- **BGE chunk embeddings:** `BAAI/bge-base-en-v1.5` embeds speaker-aware conversational chunks locally. Exact cosine search is used for this six-file corpus; HNSW is the scale-out index and should be monitored for recall loss.
- **Candidate union plus reranker:** raw FTS and cosine scores are not comparable. Both branches maximize recall, then `ms-marco-MiniLM-L-6-v2` scores individual result utterances directly. This prevents a host question from receiving the relevance of a guest answer that happens to follow it.
- **Question-answer alternative:** `hybrid_alt` gives a candidate answer its immediately preceding question as context only when speakers change, the preceding turn is a question, and the gap is at most seven seconds. It never scores a question with its following answer. This is evaluated independently from the default target-only hybrid strategy.
- **RRF baseline:** RRF (`k=60`) remains implemented as a non-reranking baseline.

The evaluation compares lexical, semantic, RRF, target-only hybrid, and the question-answer alternative. The shipped default follows the strongest validated strategy.

## Production metrics

Measure retrieval Recall@k, Precision@k, MRR, nDCG, zero-result rate, and query/category drift. Separately measure WER, diarization error/JER, timestamp error, transcription failure rate, ingestion throughput, embedding/reranker CPU and memory, p50/p95/p99 latency, index size, and hosted transcription cost.

At scale, partition corpus and vector indexes by tenant, filter metadata before retrieval, enqueue transcription/embedding jobs, batch model inference, monitor HNSW recall against exact-scan samples, and maintain a separately annotated ASR/diarization quality set.
