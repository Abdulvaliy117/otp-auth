#!/bin/sh
set -e

# Миграции и статика — только для web, воркеры стартуют сразу
if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
