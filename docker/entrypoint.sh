#!/bin/bash
set -e

echo "Starting Horilla CRM..."

# Wait for PostgreSQL to be ready (with timeout)
echo "Waiting for PostgreSQL..."
MAX_TRIES=30
COUNT=0
while ! nc -z db 5432; do
  COUNT=$((COUNT + 1))
  if [ "$COUNT" -ge "$MAX_TRIES" ]; then
    echo "ERROR: PostgreSQL not available after $MAX_TRIES attempts"
    exit 1
  fi
  sleep 1
done
echo "PostgreSQL is ready!"

# Run migrations
python manage.py migrate --noinput

# Compile .po translation catalogs to .mo -- not done at build time (unlike
# the HR image), and *.mo is gitignored, so this must happen before the
# server starts or every template falls back to English regardless of the
# active language.
python manage.py compilemessages

# Collect static files
python manage.py collectstatic --noinput

echo "Starting server..."
exec "$@"
