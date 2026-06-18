.PHONY: dev worker migrate test test-local lint format typecheck clean help

PYTHON := python
PYTEST := pytest
COMPOSE := docker-compose
COMPOSE_TEST := docker-compose -f docker-compose.test.yml

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ── Docker targets ─────────────────────────────────────────────────────────────

dev: ## Start full stack (API + worker + DB + Redis)
	$(COMPOSE) up --build

dev-d: ## Start full stack in background
	$(COMPOSE) up --build -d

down: ## Stop all containers
	$(COMPOSE) down

down-v: ## Stop all containers and remove volumes
	$(COMPOSE) down -v

migrate: ## Run Alembic migrations inside Docker
	$(COMPOSE) run --rm migrate alembic upgrade head

logs: ## Tail logs for all services
	$(COMPOSE) logs -f

logs-api: ## Tail API logs
	$(COMPOSE) logs -f api

logs-worker: ## Tail worker logs
	$(COMPOSE) logs -f worker

# ── Test targets ───────────────────────────────────────────────────────────────

test: ## Run tests in isolated Docker environment
	$(COMPOSE_TEST) up --build --abort-on-container-exit
	$(COMPOSE_TEST) down -v

test-local: ## Run tests locally (requires .venv activated)
	$(PYTEST) -v --tb=short --cov=src --cov-report=term-missing

test-local-fast: ## Run tests locally without coverage
	$(PYTEST) -v --tb=short -x

# ── Code quality ───────────────────────────────────────────────────────────────

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Auto-format code with ruff
	ruff format src/ tests/
	ruff check --fix src/ tests/

typecheck: ## Run mypy type checker
	mypy src/

check: lint typecheck ## Run all checks (lint + types)

# ── Local development helpers ──────────────────────────────────────────────────

install: ## Install dev dependencies into active venv
	pip install -r requirements-dev.txt

migrate-local: ## Run migrations locally
	alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	alembic revision --autogenerate -m "$(MSG)"

clean: ## Remove cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage
