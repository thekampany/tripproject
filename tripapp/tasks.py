# tasks.py

from django.utils import timezone
from django_q.models import Schedule
from .models import Badge, Tripper, BadgeAssignment, Trip, Location, ImmichPhotos
import requests
from datetime import datetime, timedelta

def assign_badges():
    today = timezone.now().date()
    badges = Badge.objects.filter(assignment_date=today)
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    for badge in badges:
        for trip in active_trips:
            trippers = trip.trippers.all()
            print(f"Found {trippers.count()} trippers for trip: {trip.name}")
            for tripper in trippers:
                tripper.badges.add(badge)
                tripper.save()
                BadgeAssignment.objects.create(tripper=tripper, badge=badge, trip=trip)
                print(f"Badge {badge.name} assigned to Tripper {tripper.name} for Trip {trip.name}.")


if not Schedule.objects.filter(func='tripapp.tasks.assign_badges').exists():
    Schedule.objects.create(
        func='tripapp.tasks.assign_badges',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )

def fetch_locations_for_tripper():
    today = timezone.now()
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)
    for trip in active_trips:
        for tripper in trip.trippers.all():
            last_location = Location.objects.filter(tripper=tripper).order_by('-timestamp').first()
            start_date = last_location.timestamp if last_location else today

            if tripper.api_url:
                url = f"{tripper.api_url}?api_key={tripper.api_key}&start_at={start_date.strftime('%Y-%m-%d')}"
                response = requests.get(url)
                data = response.json()

                for point in data:
                    Location.objects.create(
                        tripper=tripper,
                        latitude=point['latitude'],
                        longitude=point['longitude'],
                        timestamp=timezone.make_aware(datetime.fromtimestamp(point['timestamp']))
                    )

if not Schedule.objects.filter(func='tripapp.tasks.fetch_locations_for_tripper').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_locations_for_tripper',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )


def fetch_and_store_immich_photos(tripper_id):
    taken_before = datetime.now()
    taken_after = taken_before - timedelta(days=1)
    taken_before = taken_before.isoformat() + 'Z'
    taken_after = taken_after.isoformat() + 'Z'

    url = ""
    headers = {"x-api-key": "YOUR_API_KEY"}  
    payload = {
        "takenAfter": taken_after,
        "takenBefore": taken_before,
        "withExif": True
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        print("Failed to fetch data from Immich API")
        return
    
    data = response.json()
    assets = data.get("assets", {}).get("items", [])

    try:
        tripper = Tripper.objects.get(id=tripper_id)
    except Tripper.DoesNotExist:
        print("Tripper not found")
        return

    for item in assets:
        exif_info = item.get("exifInfo", {})
        ImmichPhotos.objects.update_or_create(
            tripper=tripper,
            immich_photo_id=item["id"],
            defaults={
                "latitude": exif_info.get("latitude"),
                "longitude": exif_info.get("longitude"),
                "city": exif_info.get("city"),
                "timestamp": make_aware(datetime.fromisoformat(item["fileCreatedAt"].replace("Z", "")))
            }
        )