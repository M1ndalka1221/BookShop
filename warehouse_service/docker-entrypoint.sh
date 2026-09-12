#!/bin/sh
set -e

echo "Waiting for PostgreSQL ($DB_HOST:$DB_PORT)..."
if [ -n "$DB_HOST" ]; then
    while ! nc -z "$DB_HOST" "$DB_PORT"; do
        sleep 0.5
    done
    echo "PostgreSQL is online and ready."
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

echo "Setting up initial roles, groups, and service accounts..."
python manage.py setup_roles

echo "Collecting static assets..."
python manage.py collectstatic --noinput --clear

exec "$@"
