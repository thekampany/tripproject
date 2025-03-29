#!/bin/sh

/usr/src/app/wait-for-it.sh db:5432 --timeout=30 --strict -- echo "Database is up"

python manage.py makemigrations --noinput
python manage.py migrate --noinput
python manage.py seed_global_badges

python manage.py shell << 'EOF'
tasks = [
    ('tripapp.tasks.fetch_locations_for_tripper', "fetch_locations"),
    ('tripapp.tasks.assign_badges', "assign_badges"),
    ('tripapp.tasks.fetch_and_store_immich_photos', "fetch_photos"),
]

for func, name in tasks:
    if not Schedule.objects.filter(func=func).exists():
        print(f"Creating scheduled task '{name}' ...")
        Schedule.objects.create(
            func=func,
            schedule_type=Schedule.HOURLY,
            repeats=-1
        )
    else:
        print(f"Scheduled task '{name}' already exists.")
EOF


if pgrep -f "python manage.py qcluster" > /dev/null; then
    echo "qcluster is already running"
else
    echo "Starting qcluster..."
    python manage.py qcluster &
fi


exec "$@"
