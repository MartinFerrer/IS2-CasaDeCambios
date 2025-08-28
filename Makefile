.PHONY: build up down migrate logs

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

# UV
test: # Correr testeos unitarios de pytest en local (Se debe usar sqlite, TODO: configurar mejor)
	uv run --env-file ..\.env.dev pytest
