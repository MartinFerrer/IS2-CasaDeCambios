.PHONY: build up down migrate logs sync precommit precommit-all

# DOCKER DEV ENVIROMENT:

build:
	docker compose -f docker-compose.dev.yml build

up:
	docker compose -f docker-compose.dev.yml up --build

down:
	docker compose -f docker-compose.dev.yml down

migrate:
	docker compose -f docker-compose.dev.yml exec web uv run python manage.py migrate

logs:
	docker compose -f docker-compose.dev.yml logs -f

# LOCAL DEV:

sync:
	uv sync --all-extras

precommit-install:
	uv run pre-commit install

precommit:
	uv run pre-commit run

precommit-all:
	uv run pre-commit run --all-files
