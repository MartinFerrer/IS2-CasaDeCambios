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

# Exec the command (runserver, gunicorn, etc.)
exec "$@"
