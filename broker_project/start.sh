#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "🔄 Checking database connection..."
python manage.py migrate --check || echo "Database not initialized yet."

echo "⌛ Waiting for database..."
sleep 5

echo "📦 Running Django migrations..."
python manage.py migrate --noinput

echo "👤 Creating admin user if missing..."
python manage.py shell <<'PY'
from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("✅ Created admin (admin / admin123)")
    else:
        print("ℹ️ Admin already exists")
except Exception as e:
    print("⚠️ Admin creation failed:", e)
PY

echo "🚀 Starting Gunicorn server..."
exec gunicorn broker_project.wsgi:application --log-file -
