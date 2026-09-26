# aud-look AI Usage and Coding-Agent Disclosure

## Systems used and scope

Two OpenAI assistants supported development in distinct phases:

- **ChatGPT** was used before implementation as an architecture sounding board. The user asked targeted follow-up questions, compared alternatives, and turned the resulting decisions into the detailed implementation requirements supplied to the coding agent.
- **OpenAI Codex** was used as the coding agent to implement, debug, test, evaluate, and document the agreed design.

Gemini 3.5 Transcribe was used separately as the application's hosted transcription service, not as a coding or architecture agent. No API key, credential value, or Gemini remote file identifier is included in this record.

## Architecture brainstorming with ChatGPT

The architecture was developed through an iterative conversation rather than accepted from one generated response. The user began with the hackathon constraints and an initial idea of combining keyword and semantic search with hosted transcription. ChatGPT was then prompted to compare concrete alternatives and explain their tradeoffs.

| Question directed to ChatGPT | Alternatives discussed | Decision carried into `aud-look` |
|---|---|---|
| Local or hosted transcription? | Gemini, Deepgram, local Whisper-style models | Use hosted Gemini because hosted transcription is permitted; normalize its output behind a provider-independent contract. |
| What should be indexed and returned? | Words, utterances, fixed chunks, conversational windows | Retrieve semantic chunks for context but return utterances for precise speaker and timestamp evidence. |
| Is PostgreSQL FTS enough without BM25? | `ts_rank_cd`, OpenSearch/Elasticsearch BM25, sparse neural retrieval | Use PostgreSQL FTS plus literal matching for this corpus; document BM25 as a scale-out option. |
| Can vector search replace keyword search? | Dense-only retrieval versus lexical plus dense retrieval | Keep both: lexical search answers whether a term was said; dense search finds related ideas. |
| How should lexical and semantic scores be combined? | Weighted score fusion, RRF, candidate union plus reranking | Union and deduplicate candidates, then use a common local cross-encoder score; retain RRF as a baseline. |
| Are embeddings needed for utterances and chunks? | Dual embedding storage versus chunk-only embeddings | Embed chunks only; map matched chunks to utterances and let the reranker localize relevance. |
| How should conversational references be handled? | Target-only versus neighboring-turn context | Initially propose neighbor-aware reranking, then validate it empirically rather than treating it as automatically better. |
| What proves the design works? | Architecture-only justification versus labeled ablations | Compare lexical, semantic, RRF, and reranked hybrid using Recall@k, MRR, latency, and category-level analysis. |

This reasoning established the design principle that **retrieval granularity and evidence granularity do not need to be the same**. It also framed the system as a conventional information-retrieval pipeline - high-recall candidate generation, high-precision reranking, precise evidence attribution, and quantitative evaluation - rather than an LLM search agent.

The conversation explicitly considered and rejected extra infrastructure that did not improve the hackathon objective: OpenSearch solely for BM25, Ollama as an additional model-serving layer, LangChain/LangGraph, an LLM-based search agent, multiple databases, and duplicate utterance embeddings.

One brainstorming decision changed after implementation. Neighboring turns were initially proposed as reranker context to resolve pronouns and question-answer relationships. Real searches showed that symmetric previous/target/next context could instead make a host's question inherit relevance from the guest's answer. The user identified this qualitative failure; Codex implemented target-only `hybrid` as the default and a narrower asymmetric question-answer experiment as `hybrid_alt`. The evaluation then showed equal Recall@5 with no ranking benefit from the alternative despite its additional pair-scoring work, supporting the simpler default.

## Direction supplied by the user

The user provided or decided:

- the complete hackathon problem statement and required submission format;
- six podcast clips and contextual descriptions of their subject matter;
- the architecture requirements distilled from the ChatGPT brainstorming, specifying Python 3.11, Docker Compose, PostgreSQL/pgvector, FastAPI, Streamlit, Gemini transcription, local BGE embeddings, a local cross-encoder, hybrid retrieval, timestamped evidence, and Recall@k evaluation;
- the requirement that cached transcripts remain reproducible and that embeddings, indexing, retrieval, and reranking run locally;
- acceptance targets for ingestion validity, Recall@5, exact/entity HitRate@3, warm latency, secret handling, and automated coverage; and
- continuing product decisions during debugging and relevance review.

The user supplied the Gemini key through a local uncommitted `.env` file. The value was never requested for documentation and was not written into source files or logs by the agent.

## Summarized collaboration trace

| User direction or observation | Agent work produced |
|---|---|
| Use the architecture decisions developed through ChatGPT brainstorming as implementation requirements. | Converted the dual-granularity retrieve-then-rerank design into database mappings, retrieval strategies, configuration, and tests. |
| Implement the supplied architecture plan in an empty repository. | Created the Docker services, Alembic schema, ingestion pipeline, retrieval modules, API, Streamlit UI, tests, evaluation runner, runbook, and architecture record. |
| Explain environment variables and the `migrate`, `transcribe`, and `ingest` targets. | Documented the runtime flow and kept the API key as the only required transcription secret. |
| Gemini SDK raised `AudioTranscriptionConfig` errors. | Checked the active SDK contract, updated the pinned Google GenAI dependency, moved transcription to the Interactions API, and added response-parsing tests. |
| Upload failed because a filename contained a non-ASCII em dash. | Renamed dataset files to stable ASCII names and added an ASCII temporary-upload path as a defensive measure. |
| Word timestamps were reported as non-monotonic. | Determined that diarized cross-talk can produce overlapping word intervals, sorted annotations by start time, allowed valid overlap, and retained rejection of true reversals. |
| Review the completed transcripts for contract fitness. | Validated checksums, cache provenance, two-speaker labels, timestamp bounds, utterance construction, chunk coverage, and secret absence; identified proper-name transcription variants and recommended audio spot-checks. |
| Generate evaluation labels from the real transcripts. | Drafted 36 timestamp-grounded queries across six categories with a balanced 24/12 split. The user reviewed the golden spans before final submission use. |
| Run retrieval-quality tests. | Ran unit/integration tests, live representative searches, strategy ablations, and holdout evaluation; generated JSON and Markdown reports. |
| Host questions sometimes ranked above guest answers. | Diagnosed relevance leakage from symmetric previous/target/next reranking. Made target-only reranking the default `hybrid`, implemented an asymmetric Q/A-pair experiment as `hybrid_alt`, narrowed hard literal priority for natural-language questions, and exposed both strategies in the UI. |
| Show real speaker names and make known transcription variants searchable without altering evidence. | Added user-verified, per-episode speaker presentation metadata and query-time lexical entity equivalence groups while preserving raw diarization labels and canonical transcripts. |
| Re-run evaluation after the search metadata changes. | Found that repeat ingestion retained orphaned semantic chunks, which reduced effective semantic candidate diversity. Corrected episode-level chunk replacement and revalidated on a clean database before reporting metrics. |
| Prepare submission documentation and disclose coding-agent use. | Consolidated design rationale, success criteria, measured achievement, limitations, production considerations, and this collaboration record into Markdown and PDF deliverables. |

## Division of responsibility

### User-owned decisions and review

- Selected and supplied the audio corpus for the hackathon workspace; public redistribution status remains to be documented per clip.
- Directed the ChatGPT architecture exploration, selected among the alternatives, and supplied the resulting requirements and acceptance criteria to Codex.
- Kept the Gemini credential outside versioned artifacts.
- Ran and reviewed the real transcription and ingestion workflow.
- Reviewed the timestamp-grounded golden evaluation spans.
- Identified qualitative ranking behavior that automated metrics did not fully expose.
- Directed the final public strategy names and requested the submission package.

### Codex-produced implementation

- Repository scaffolding and Docker Compose runtime.
- PostgreSQL/pgvector schema, migrations, ingestion, and idempotent upserts.
- Gemini transcription adapter and canonical cache format.
- Word validation, utterance formation, conversational chunking, local embeddings, and indexes.
- Lexical, semantic, RRF, target-only hybrid, and Q/A-pair alternative retrieval.
- FastAPI endpoints, Streamlit UI, reviewed speaker-name presentation mappings, query-time entity aliases, tests, evaluation code, reports, and documentation.
- Debugging patches in response to observed SDK, filename, timestamp, and ranking failures.

## Verification record

Completed on 2026-09-26:

- Ingested six episodes totaling 52 minutes and 29 seconds into 395 utterances and 130 semantic chunks.
- Validated every transcript cache against audio SHA-256 and transcription-configuration hash.
- Confirmed exactly two diarization labels per episode, valid timestamp bounds, and complete utterance-to-chunk mapping.
- Applied Alembic migration `0001_initial` and verified PostgreSQL FTS, pgvector cosine ordering, idempotent upserts, and chunk membership through integration tests.
- Ran the deterministic suite against a clean migrated PostgreSQL instance: **22 passed**, with the separately marked real-corpus evaluation deselected.
- Ran `make evaluate`: **1 slow evaluation test passed**, producing the holdout ablation report.
- Measured holdout `hybrid` Recall@5 at **0.833**, MRR at **0.590**, and warm p95 latency at **607 ms** after an explicit untimed warm-up query.
- Confirmed the live Jordan Noone question ranks the guest's answer above the host's question.

## Boundaries and limitations of agent use

Neither ChatGPT nor Codex independently established audio licensing, listened to every audio interval, identified speakers by biometric inference, or supplied the Gemini credential. ChatGPT's architecture suggestions were treated as alternatives for user selection, not authoritative requirements. Audio-level validation and transcript-derived labels remained subject to user review. Evaluation limitations and unsuccessful alternatives are retained in the submission rather than omitted.
