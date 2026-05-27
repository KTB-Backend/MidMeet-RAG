# Repository Guidelines

## Project Priority

This repository is for "어디서 만날래?", a RAG-based meeting-place recommendation service. The priority is the RAG pipeline harness, not the web app. Build and verify this flow first: seed data -> embedding -> Chroma storage -> hybrid scoring -> grounded recommendation generation. UI, Kakao Map rendering, sessions, and collaboration features come later.

## Project Structure

- `docs/project-brief.md`: product and RAG design source of truth.
- `docs/prompts/`: grounded generation prompt templates.
- `data/seeds/raw/`: manually verified factual seed sources.
- `data/seeds/processed/`: normalized records ready for embedding.
- `data/chroma/`: local Chroma indexes; ignored and never committed.
- `packages/rag_core/`: reusable RAG logic for loading, embedding, retrieval, scoring, prompt assembly, and generation adapters.
- `apps/rag_api/`: API layer only; keep RAG logic out of API code.
- `scripts/`: repeatable harness commands for indexing, querying, and evaluation.
- `tests/`: deterministic automated tests.
- `evals/`: slower retrieval and recommendation-quality checks.

## Development Rules

Use Python 3.11. Keep the core pipeline runnable without a web server. Separate geocoding, centroid calculation, seed validation, embedding, Chroma indexing, retrieval, distance normalization, hybrid scoring, and generation. Model names, Chroma paths, API keys, and scoring weights must be configurable, not hard-coded.

Expected local flow once tooling exists:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pytest tests/
python -m scripts.index_seeds
python -m scripts.query_harness
```

## Data Rules

Do not crawl. Use Kakao Local API only for allowed place, coordinate, and live search data. Seed atmosphere text must be manually written or verified from legitimate factual sources. Never store LLM-invented atmosphere descriptions as factual seed data. Each seed should represent one real venue and include coordinates, provenance, structured attributes where available, and atmosphere text specific enough for semantic search.

Recommendations must cite or expose retrieved seed evidence. If a claim is not in retrieved seeds or metadata, omit it or state uncertainty.

## Testing Rules

Use `pytest`. Name tests `test_<behavior>()` in `tests/test_<module>.py`. Cover centroid math, distance normalization, score weighting, metadata preservation, seed validation, retrieval result shape, and prompt grounding constraints. Put model-dependent or Chroma-heavy checks in `evals/` with fixed fixtures and expected ranking behavior.

## Completion Criteria

A RAG task is complete only when it has a documented command, deterministic tests for changed logic, and source-grounded behavior. Indexing work must verify Chroma records and metadata. Retrieval work must expose semantic score, distance score, and final hybrid score. Generation work must verify output is constrained to retrieved seed evidence.

## Commit & PR Guidelines

The current history only has `Initial commit`, so use imperative commits such as `Add seed validation harness`. PRs should state the pipeline step changed, data assumptions, commands run, and evaluation gaps. Include sample query output for retrieval or generation changes.

## Security

Keep `.env` local. Do not commit API keys, Chroma indexes, SQLite files, downloaded model weights, private source files, or generated artifacts that cannot be reproduced.
