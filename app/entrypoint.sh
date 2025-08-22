#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."
    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done
    echo "PostgreSQL started"
fi

# wait for generated tailwind css in dev (optional)
if [ "$WAIT_FOR_CSS" = "1" ]; then
  echo "Waiting for output.css..."
  attempts=0
  while [ ! -f /app/static/css/output.css ] && [ $attempts -lt 120 ]; do
    attempts=$((attempts + 1))
    sleep 0.5
  done
  if [ ! -f /app/static/css/output.css ]; then
    echo "Warning: /app/static/css/output.css not found after timeout"
  else
    echo "Found output.css"
  fi
fi

exec "$@"
