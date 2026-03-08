.PHONY: help install dev build lint test clean up down logs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ─── Dependencies ────────────────────────────────────────────────────

install: ## Install all dependencies (backend + frontend)
	pip install -r requirements.txt
	cd web && pnpm install

# ─── Development ─────────────────────────────────────────────────────

dev: ## Start all services via Docker Compose
	docker compose up -d

up: dev ## Alias for dev

down: ## Stop all services
	docker compose down

logs: ## Tail logs from all services
	docker compose logs -f --tail=50

web-dev: ## Start frontend dev server (Vite, port 3000)
	cd web && pnpm dev

# ─── Code Quality ────────────────────────────────────────────────────

lint: ## Run all linters
	ruff check app/ tests/ scripts/
	cd web && pnpm lint

format: ## Auto-format code
	ruff format app/ tests/ scripts/

test: ## Run backend tests
	pytest tests/ -v --ignore=tests/integration/ --ignore=tests/manual/

# ─── Build ───────────────────────────────────────────────────────────

build: ## Build Docker images
	docker compose build

build-web: ## Build frontend only
	cd web && pnpm build

# ─── Setup ───────────────────────────────────────────────────────────

init: ## First-time setup: generate secrets, copy env, install deps
	./scripts/init-secrets.sh
	@test -f .env || cp .env.example .env
	$(MAKE) install

clean: ## Remove Docker volumes and build artifacts
	docker compose down -v
	rm -rf .docker-data web/dist web/node_modules
