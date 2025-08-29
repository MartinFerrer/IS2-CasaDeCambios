.PHONY: build up up-detached down down-rm-volumes migrate makemigrations logs sync precommit-install precommit precommit-all test test-local doc doc-local shell

# Ruta al archivo de docker-compose (ajusta si es necesario)
COMPOSE_FILE = docker-compose.dev.yml

# ENTORNO DE DESARROLLO DOCKER
build:
	docker compose -f $(COMPOSE_FILE) build

up:
	docker compose -f $(COMPOSE_FILE) up --build

up-detached:
	docker compose -f $(COMPOSE_FILE) up -d --build

down:
	docker compose -f $(COMPOSE_FILE) down

# Elimina también los volúmenes
down-rm-volumes:
	docker compose -f $(COMPOSE_FILE) down -v

# Se recomienda usar run --rm --no-deps para no necesitar un contenedor web en ejecución
migrate:
	docker compose -f $(COMPOSE_FILE) run --rm --no-deps web uv run python manage.py migrate

makemigrations:
	docker compose -f $(COMPOSE_FILE) run --rm --no-deps web uv run python manage.py makemigrations

logs:
	docker compose -f $(COMPOSE_FILE) logs -f

# HERRAMIENTAS LOCALES / DESARROLLO 
# Sincroniza el entorno de desarrollo con uv (local)
sync:
	uv sync --all-extras

# Instala los hooks de pre-commit en git localmente
precommit-install:
	uv run pre-commit install

# Ejecuta las verificaciones de pre-commit en los archivos modificados
precommit:
	uv run pre-commit run

# Ejecuta las verificaciones de pre-commit en todos los archivos
precommit-all:
	uv run pre-commit run --all-files

# TESTS / DOCUMENTACIÓN
# Ejecuta el servicio de pruebas dentro de docker
test:
	docker compose -f $(COMPOSE_FILE) run --rm test

# Ejecuta pytest localmente (requiere un entorno virtual local con dependencias)
test-local:
	uv run --env-file ../.env.dev pytest

# Construye la documentación en docker (contenedor web / uv)
doc:
	docker compose -f $(COMPOSE_FILE) run --rm --no-deps web uv run sphinx-build -b html docs docs/_build/html

# Construye la documentación localmente (requiere dependencias de desarrollo locales)
doc-local:
	uv run --extra dev sphinx-build -b html docs docs/_build/html

# Accede a la terminal del contenedor web en ejecución (si está corriendo)
shell:
	docker compose -f $(COMPOSE_FILE) exec web bash