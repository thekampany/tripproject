#!/bin/sh

/usr/src/app/wait-for-it.sh db:5432 --timeout=30 --strict -- echo "Database is up"

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py seed_global_badges

# Superuser
SUPERUSER_NAME=${SUPERUSER_NAME:-admin}
SUPERUSER_EMAIL=${SUPERUSER_EMAIL:-admin@example.com}
SUPERUSER_PASSWORD=${SUPERUSER_PASSWORD:-adminpassword}

python manage.py shell << EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()

if not User.objects.filter(is_superuser=True).exists():
    print("Creating superuser...")
    User.objects.create_superuser(
        username=os.getenv('SUPERUSER_NAME', '$SUPERUSER_NAME'),
        email=os.getenv('SUPERUSER_EMAIL', '$SUPERUSER_EMAIL'),
        password=os.getenv('SUPERUSER_PASSWORD', '$SUPERUSER_PASSWORD')
    )
else:
    print("Superuser already exists.")
EOF



python manage.py shell << 'EOF'
from django_q.models import Schedule
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
