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
    today = timezone.now()
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)
    
    for trip in active_trips:
        for tripper in trip.trippers.all():
            last_location = Location.objects.filter(tripper=tripper).order_by('-timestamp').first()
            start_date = last_location.timestamp if last_location else today - timedelta(days=1)  
            end_date = start_date + timedelta(hours=1)  

            while start_date < today:
                if tripper.dawarich_url:
                    url = (
                        f"{tripper.dawarich_url}?api_key={tripper.dawarich_api_key}"
                        f"&start_at={start_date.isoformat()}"
                        f"&end_at={end_date.isoformat()}"
                        f"&per_page=100000"
                    )

                    response = requests.get(url)
                    if response.status_code != 200:
                        print(f"Failed to fetch locations for tripper {tripper.id}")
                        break  

                    try:
                        data = response.json()
                    except ValueError:
                        print(f"Invalid JSON response for tripper {tripper.id}")
                        break

                    if not data:  
                        print(f"No data returned for interval {start_date} to {end_date}")
                        break


                    tolerance = 0.00005
                    previous_lat = None
                    previous_long = None

                    for point in data:
                        current_lat = point['latitude']
                        current_long = point['longitude']


                        if previous_lat is not None and previous_long is not None:
                            if abs(current_lat - previous_lat) < tolerance and abs(current_long - previous_long) < tolerance:
                                continue

                        Location.objects.create(
                            tripper=tripper,
                            latitude=current_lat,
                            longitude=current_long,
                            timestamp=make_aware(datetime.fromtimestamp(point['timestamp']))
                        )
                        previous_lat = current_lat
                        previous_long = current_long



                    start_date = end_date
                    end_date = start_date + timedelta(hours=1)

                    time.sleep(10)

if not Schedule.objects.filter(func='tripapp.tasks.fetch_locations_for_tripper').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_locations_for_tripper',
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )


def fetch_and_store_immich_photos():
    today = timezone.now().date()
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)
    for trip in active_trips:
        #print(trip)
        for tripper in trip.trippers.all():
            last_photolocation = ImmichPhotos.objects.filter(tripper=tripper).order_by('-timestamp').first()
            #print(last_photolocation.timestamp)
            start_date = last_photolocation.timestamp if last_photolocation else timezone.make_aware(datetime.combine(today, datetime.min.time()))
            #print(start_date.isoformat())
            #print(tripper.immich_url)
            if tripper.immich_url:
                url = f"{tripper.immich_url}api/search/metadata"
                headers = {"x-api-key": tripper.immich_api_key}  
                payload = {
                    "updatedAfter": start_date.isoformat(),
                    "withExif": True,
                    "type": "IMAGE"
                }
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code != 200:
                    print("Failed to fetch data from Immich API")
                    return
        
                data = response.json()
                assets = data.get("assets", {}).get("items", [])

                for item in assets:
                    exif_info = item.get("exifInfo", {})
                    if exif_info.get("latitude"):
                        ImmichPhotos.objects.update_or_create(
                        tripper=tripper,
                        immich_photo_id=item["id"],
                        latitude = exif_info.get("latitude"),
                        longitude = exif_info.get("longitude"),
                        city = exif_info.get("city"),
                        timestamp = make_aware(datetime.fromisoformat(item["fileCreatedAt"].replace("Z", "")))
                        )
                        # the photo is available at tripper.immich_url/photos/immich_photo_id; user needs to be logged in etc.
                        # saving the thumbnail
                        url = f"{tripper.immich_url}/api/assets/{item['id']}/thumbnail"
                        headers = {
                            'x-api-key': f"{tripper.immich_api_key}",
                            'Accept': 'application/octet-stream',
                        }

                        try:
                            response = requests.get(url, headers=headers)
                            response.raise_for_status()  

                            if response.content:
                                file_name = f"{item['id']}_thumbnail.jpg"
                                photo, created = ImmichPhotos.objects.update_or_create(
                                    tripper=tripper,
                                    immich_photo_id=item["id"],
                                    defaults={
                                        "latitude": exif_info.get("latitude"),
                                        "longitude": exif_info.get("longitude"),
                                        "city": exif_info.get("city"),
                                        "timestamp": make_aware(datetime.fromisoformat(item["fileCreatedAt"].replace("Z", ""))),
                                    }
                                )
                                photo.thumbnail.save(file_name, ContentFile(response.content))
                                photo.save()
                                print(f"Thumbnail saved for {item['id']}")
                            else:
                                print(f"No content received for {item['id']}")

                        except Exception as e:
                            print(f"Error retrieving thumbnail for {item['id']}: {e}")




if not Schedule.objects.filter(func='tripapp.tasks.fetch_and_store_immich_photos').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_and_store_immich_photos',
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )
