#!/bin/bash

set -e

# Run database migrations and static collection only when starting the web server
if [ "$1" = "gunicorn" ] || [ "$1" = "python" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput

    echo "Collecting static files..."
    python manage.py collectstatic --noinput

    echo "Starting Django server..."
fi

exec "$@"