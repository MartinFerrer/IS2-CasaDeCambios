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
uv run python manage.py migrate

# Collect static files if in production
if [ "${DEBUG}" = "False" ] || [ "${DEBUG}" = "false" ] || [ "${DEBUG}" = "0" ]; then
    echo "Collecting static files..."
    uv run python manage.py collectstatic --noinput
fi

# Exec the main command (runserver, gunicorn, etc.)
exec "$@"
