#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "🔄 Checking database connection..."
python manage.py migrate --check || echo "Database not initialized yet."

echo "⌛ Waiting for database..."
sleep 5

echo "📦 Running Django migrations..."
python manage.py migrate --noinput

echo "🚀 Starting Gunicorn server..."
exec gunicorn broker_project.wsgi:application --log-file -
