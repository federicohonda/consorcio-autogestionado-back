.PHONY: install dev up-local down-local up-remote down-remote migrate lint

install:
	poetry install

dev:
	PYTHONPATH=. poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

up-local:
	docker compose -f docker-compose.local.yml up --build

down-local:
	docker compose -f docker-compose.local.yml down

up-remote:
	docker compose -f docker-compose.remote.yml up --build

down-remote:
	docker compose -f docker-compose.remote.yml down

migrate:
	supabase db push

lint:
	poetry run ruff check src/

lint-fix:
	poetry run ruff check src/ --fix
