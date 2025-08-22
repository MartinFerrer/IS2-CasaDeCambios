.PHONY: build up down migrate logs

build:
	docker compose -f docker-compose.dev.yml build

up:
	docker compose -f docker-compose.dev.yml up --build

down:
	docker compose -f docker-compose.dev.yml down

migrate:
	docker compose -f docker-compose.dev.yml exec web python manage.py migrate

logs:
	docker compose -f docker-compose.dev.yml logs -f
