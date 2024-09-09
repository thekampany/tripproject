#!/bin/sh

/usr/src/app/wait-for-it.sh db:5432 --timeout=30 --strict -- echo "Database is up"

python manage.py migrate --noinput

exec "$@"
