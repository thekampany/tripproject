# tasks.py

from django.utils import timezone
from django_q.models import Schedule
from .models import Badge, Tripper, BadgeAssignment, Trip, Location, ImmichPhotos
import requests
from datetime import datetime, timedelta
from django.core.files.base import ContentFile

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
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )


import time
from datetime import timedelta
from django.utils.timezone import make_aware

def fetch_locations_for_tripper():
    logs = []
    today = timezone.now()
    logs.append(f"Task start: {today}")
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    for trip in active_trips:
        logs.append(f"Trip: {trip.name}")
        for tripper in trip.trippers.all():
            last_location = Location.objects.filter(tripper=tripper).order_by('-timestamp').first()
            start_date = last_location.timestamp if last_location else today - timedelta(days=1)
            logs.append(f"last location for {tripper.name} stored at: {start_date}")
            end_date = start_date + timedelta(hours=1)
            if tripper.dawarich_url:
                while start_date < today:
                    url = (
                        f"{tripper.dawarich_url}?api_key={tripper.dawarich_api_key}"
                        f"&start_at={start_date.isoformat()}"
                        f"&end_at={end_date.isoformat()}"
                        f"&per_page=100000&order=asc"
                    )

                    try:
                        response = requests.get(url)
                        response.raise_for_status()  
                        data = response.json()
                    except requests.RequestException as e:
                        logs.append(f"HTTP error for tripper {tripper.id}: {e}")
                        break
                    except ValueError:
                        logs.append(f"Invalid JSON response for tripper {tripper.id}")
                        break

                    if not data:
                        logs.append(f"No data returned for interval {start_date} to {end_date}")
                        start_date = end_date
                        end_date += timedelta(hours=1)
                        continue

                    tolerance = 0.0001
                    previous_lat, previous_long = None, None
                    location_count = 0

                    for point in data:
                        current_lat = point.get('latitude')
                        current_long = point.get('longitude')
                        timestamp = point.get('timestamp')

                        if not current_lat or not current_long or not timestamp:
                            logs.append("Invalid point data; skipping.")
                            continue

                        current_lat = float(current_lat)
                        current_long = float(current_long)

                        if (
                            previous_lat is None
                            or previous_long is None
                            or abs(current_lat - previous_lat) >= tolerance
                            or abs(current_long - previous_long) >= tolerance
                        ):
                            Location.objects.create(
                                tripper=tripper,
                                latitude=current_lat,
                                longitude=current_long,
                                timestamp=make_aware(datetime.fromtimestamp(timestamp))
                            )
                            previous_lat, previous_long = current_lat, current_long
                            location_count += 1
                    logs.append(f"Processed {len(data)} points for interval {start_date} to {end_date}, added {location_count}")
                    start_date = end_date
                    end_date += timedelta(hours=1)

                    time.sleep(1) 
    logs.append(f"Task end")

    return "\n".join(logs)

if not Schedule.objects.filter(func='tripapp.tasks.fetch_locations_for_tripper').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_locations_for_tripper',
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )


def fetch_and_store_immich_photos():
    logs = []
    today = timezone.now().date()
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)
    logs.append(f"Task start: {today}")

    for trip in active_trips:
        for tripper in trip.trippers.all():
            last_photolocation = ImmichPhotos.objects.filter(tripper=tripper).order_by('-timestamp').first()
            start_date = last_photolocation.timestamp if last_photolocation else timezone.make_aware(datetime.combine(today, datetime.min.time()))
            logs.append(f"Start date for {tripper.name}: {start_date.isoformat()}")

            if tripper.immich_url:
                url = f"{tripper.immich_url}api/search/metadata"
                headers = {"x-api-key": tripper.immich_api_key}
                payload = {
                    "takenAfter": start_date.isoformat(),
                    "withExif": True,
                    "type": "IMAGE"
                }
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code != 200:
                    logs.append(f"Failed to fetch data from Immich API for tripper {tripper.name}")
                    continue

                data = response.json()
                assets = data.get("assets", {}).get("items", [])

                for item in assets:
                    exif_info = item.get("exifInfo", {})
                    if not exif_info.get("latitude"):
                        continue

                    thumbnail_url = f"{tripper.immich_url}/api/assets/{item['id']}/thumbnail"
                    headers = {
                        'x-api-key': f"{tripper.immich_api_key}",
                        'Accept': 'application/octet-stream',
                    }

                    try:
                        thumbnail_response = requests.get(thumbnail_url, headers=headers)
                        thumbnail_response.raise_for_status()

                        if thumbnail_response.content:
                            file_name = f"{item['id']}_thumbnail.jpg"

                            ImmichPhotos.objects.create(
                                tripper=tripper,
                                immich_photo_id=item["id"],
                                latitude=exif_info.get("latitude"),
                                longitude=exif_info.get("longitude"),
                                city=exif_info.get("city"),
                                timestamp=make_aware(datetime.fromisoformat(item["fileCreatedAt"].replace("Z", ""))),
                                thumbnail=ContentFile(thumbnail_response.content, file_name),
                            )
                            logs.append(f"Photo and thumbnail saved for {item['id']}")

                        else:
                            logs.append(f"No thumbnail content for {item['id']}")

                    except Exception as e:
                        logs.append(f"Error retrieving thumbnail for {item['id']}: {e}")
    logs.append(f"Task end")

    return "\n".join(logs)




if not Schedule.objects.filter(func='tripapp.tasks.fetch_and_store_immich_photos').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_and_store_immich_photos',
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )
