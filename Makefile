# SAGARDRISHTI
# Run from WSL2. See docs/DEVELOPMENT.md
.DEFAULT_GOAL := help
.PHONY: help setup up down logs test test-integration lint demo warm-cache offline evaluate ais-status quota-status docs clean

COMPOSE        := docker compose
COMPOSE_OFF    := docker compose -f docker-compose.yml -f infra/compose/docker-compose.offline.yml

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- setup --------------------------------------------------------
setup: ## Create environments and install all dependencies
	micromamba create -y -f infra/env/geo.yml
	uv venv .venv && uv pip install -r services/api/requirements.txt
	cd services/aisd  && go mod download
	cd services/aisgen && go mod download
	cd web && npm ci
	@echo ""
	@echo "  Setup complete."
	@echo "  NEXT: start the AIS recorder. It needs 3 months of runtime and"
	@echo "        AISStream has no replay. See services/aisd/README.md"

# --- stack --------------------------------------------------------
up: ## Start the full stack
	$(COMPOSE) up -d
	@echo "  console  http://localhost:5173"
	@echo "  api      http://localhost:8000/docs"

down: ## Stop the stack
	$(COMPOSE) down

logs: ## Tail all container logs
	$(COMPOSE) logs -f

offline: ## Start the stack in cache-only mode (no network)
	$(COMPOSE_OFF) up -d

# --- quality ------------------------------------------------------
test: ## Unit and contract tests
	pytest tests/ packages/ -v
	cd services/aisd && go test ./...
	cd packages/go   && go test ./...

test-integration: ## Full pipeline on a cached scene
	pytest tests/integration/ -v --timeout=900

lint: ## Lint everything
	ruff check . && ruff format --check .
	cd packages/go && go vet ./...
	cd web && npx tsc --noEmit && npm run lint

# --- data ---------------------------------------------------------
warm-cache: ## Populate the offline cache (online, 30-60 min)
	python tools/warm_cache.py --all

demo: ## Load cached demo scenarios
	python tools/build_demo_cache.py --load

check-offline: ## Verify zero outbound calls on an internal-only network
	python tools/check_offline.py

# --- ops ----------------------------------------------------------
ais-status: ## AIS recorder health - run daily in week 1, weekly after
	python tools/ais_status.py

quota-status: ## CDSE Processing Unit usage
	python tools/quota_status.py

# --- evaluation ---------------------------------------------------
evaluate: ## Regenerate all metrics and figures
	python -m ml.evaluation.run --all
	python tools/make_figures.py

# --- docs ---------------------------------------------------------
docs: ## Serve the documentation site
	mkdocs serve

clean: ## Remove build artefacts (never touches data/)
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache web/dist site
