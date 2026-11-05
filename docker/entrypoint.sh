#!/bin/sh
# Container entrypoint: validate config, wait for the database, migrate, then exec CMD.
set -eu

if [ -z "${DJANGO_SECRET_KEY:-}" ] && [ "${DJANGO_DEBUG:-false}" != "true" ]; then
  echo "ERROR: DJANGO_SECRET_KEY must be set in production (see .env.example)." >&2
  exit 1
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  attempt=1
  until python manage.py migrate --noinput; do
    if [ "$attempt" -ge "${DB_WAIT_ATTEMPTS:-15}" ]; then
      echo "ERROR: database not reachable after $attempt attempts." >&2
      exit 1
    fi
    echo "Database not ready (attempt $attempt), retrying in 2s..."
    attempt=$((attempt + 1))
    sleep 2
  done
fi

# Optional: bootstrap the platform operator account from env (idempotent).
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
  python manage.py ensure_superuser
fi

exec "$@"
