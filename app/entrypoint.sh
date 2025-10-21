#!/bin/sh
set -e

# Wait for database (only)
if [ "$DATABASE" = "postgres" ]; then
    echo "Waiting for postgres..."
    while ! nc -z "$SQL_HOST" "$SQL_PORT"; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi

# Run migrations
echo "Running migrations..."
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  uv run python manage.py migrate
else
  echo "Skipping migrations (RUN_MIGRATIONS!=1)"
fi

# Collect static files if in production
if [ "${DEBUG}" = "False" ] || [ "${DEBUG}" = "false" ] || [ "${DEBUG}" = "0" ]; then
    echo "Collecting static files..."
    uv run python manage.py collectstatic --noinput
fi

# Set default PORT for Heroku if not set
PORT=${PORT:-8000}

# Exec the main command (runserver, gunicorn, etc.)
# If no command is provided, start gunicorn
if [ $# -eq 0 ]; then
    exec uv run gunicorn --bind 0.0.0.0:$PORT global_exchange_django.wsgi:application
else
    exec "$@"
fi
