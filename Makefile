.PHONY: install dev test lint typecheck migrate docker-up docker-down check

install:
	poetry install

dev:
	poetry run uvicorn app.main:app --reload --port 8000

test:
	poetry run pytest -q

lint:
	poetry run ruff check .

typecheck:
	poetry run mypy app --strict

migrate:
	poetry run alembic upgrade head

docker-up:
	docker compose up -d

docker-down:
	docker compose down

check: lint typecheck test
