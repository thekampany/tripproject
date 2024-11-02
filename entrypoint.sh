#!/bin/sh

/usr/src/app/wait-for-it.sh db:5432 --timeout=30 --strict -- echo "Database is up"

python manage.py migrate --noinput

python manage.py shell << 'EOF'
from django_q.models import Schedule

if not Schedule.objects.filter(func='tripapp.tasks.fetch_locations_for_tripper').exists():
    print("Creating scheduled task 'fetch_locations' ...")
    Schedule.objects.create(
        func='tripapp.tasks.fetch_locations_for_tripper',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )
else:
    print("Scheduled task 'fetch_locations' already exists.")


if not Schedule.objects.filter(func='tripapp.tasks.assign_badges').exists():
    print("Scheduled task 'assign_badges' does not exist yet. Creating...")
    Schedule.objects.create(
        func='tripapp.tasks.assign_badges',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )
else:
    print("Scheduled task 'assign_badges' already exists.")
EOF

python manage.py qcluster &


exec "$@"
