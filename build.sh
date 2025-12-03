#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Run migrations
python manage.py migrate

# Create superuser from environment variables (if set)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" --username "$DJANGO_SUPERUSER_USERNAME" || true
    echo "Superuser creation attempted"
fi

# Seed data (only runs if tables are empty)
echo "Seeding initial data..."
python manage.py seed_mentors || true
python manage.py seed_benchmarks || true
echo "Seeding complete"
