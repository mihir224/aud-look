.DEFAULT_GOAL := help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "%-18s %s\\n", $$1, $$2}'

up: ## Start Postgres, API, and Streamlit
	docker compose up --build

db-up: ## Start only Postgres
	docker compose up -d db

migrate: ## Apply database migrations
	docker compose run --build --rm api alembic upgrade head

transcribe: ## Generate/cache canonical Gemini transcripts
	docker compose run --build --rm api python -m app.ingestion.pipeline transcribe

ingest: ## Normalize cached transcripts and build local indexes
	docker compose run --build --rm api python -m app.ingestion.pipeline ingest

seed: ## Transcribe if needed, then ingest
	docker compose run --build --rm api python -m app.ingestion.pipeline all

test: ## Run deterministic unit and integration tests
	docker compose run --build --rm api pytest -m "not slow"

integration: ## Migrate Postgres and run database integration tests
	$(MAKE) migrate
	docker compose run --build --rm api pytest -m integration

evaluate: ## Run the real-corpus evaluation suite after manual labels exist
	docker compose run --build --rm api pytest -m slow -q

down: ## Stop stack
	docker compose down
