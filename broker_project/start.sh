#!/usr/bin/env bash
set -o errexit
set -o pipefail

echo "⌛ Waiting for database to be ready..."
python manage.py showmigrations > /dev/null 2>&1 || sleep 5

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
        print("ℹ️ Admin user already exists")
except Exception as e:
    print("⚠️ Superuser creation failed:", e)
PY

echo "🚀 Starting Gunicorn server..."
exec gunicorn broker_project.wsgi:application --log-file -
