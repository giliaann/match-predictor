#!/bin/bash
set -e

if [ "$SKIP_INIT" = "true" ]; then
    echo "Skip django initialization commands..."
else

    echo "Running database migrations..."
    uv run python manage.py migrate --noinput

    echo "Running initialization command..."
    uv run python manage.py setup_competition --code WC

    echo "Initialization complete. Starting the application..."
fi

exec "$@"