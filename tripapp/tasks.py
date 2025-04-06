# tasks.py

from django.utils import timezone
from django.db import models
from django_q.models import Schedule
from .models import Badge, Tripper, BadgeAssignment, Trip, Location, ImmichPhotos, BingoAnswer, LogEntry, DayProgram
import requests
from datetime import datetime, timedelta
from django.core.files.base import ContentFile
from django.utils.timezone import make_aware
import pytz
import time
from .utils import generate_static_map
from django.conf import settings

def assign_badges():
    logs = []

    #assign badges on date
    today = timezone.now().date()
    logs.append(f"Start Assigning Badges on date\n")
    badges = Badge.objects.filter(assignment_date=today)
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    if badges.exists(): 
        for badge in badges:
            for trip in active_trips:
                trippers = trip.trippers.all()
                tripper_count = trippers.count()
                logs.append(f"Found {tripper_count} trippers for trip: {trip.name}")

                assignments = []
                for tripper in trippers:
                    tripper.badges.add(badge) 
                    assignments.append(BadgeAssignment(tripper=tripper, badge=badge, trip=trip))

                    logs.append(f"Badge {badge.name} assigned to Tripper {tripper.name} for Trip {trip.name}.")

                BadgeAssignment.objects.bulk_create(assignments)

    else:
        logs.append("No Badges on this date to be assigned")


    #assign badges for bingo answer uploads
    logs.append(f"Assign Badges for BingoAnswer Uploads\n")
    bingoanswerbadges = Badge.objects.filter(
        level='global', 
        achievement_method='threshold',
        threshold_type='bingo_answer_uploads'
    ).exclude(threshold_value__isnull=True)  

    if bingoanswerbadges.exists(): 
        for badge in bingoanswerbadges:
            for trip in active_trips:
                trippers = trip.trippers.all()
                logs.append(f"Found {trippers.count()} trippers for trip: {trip.name}")
                
                for tripper in trippers:
                    answer_count = BingoAnswer.objects.filter(tripper=tripper).count()
                    
                    if answer_count >= badge.threshold_value:
                        if not tripper.badges.filter(pk=badge.pk).exists(): 
                            tripper.badges.add(badge)
                            tripper.save()
                            BadgeAssignment.objects.create(tripper=tripper, badge=badge)
                            logs.append(f"Badge '{badge.name}' assigned to Tripper {tripper.name} due to {answer_count} bingo answers.")
    else:
        logs.append("No Badges for bingoanswers to be assigned")
    
    #assign badges for log entries
    logs.append(f"\n")
    logs.append(f"Assign Badges for adding Logs")
    logentrybadges = Badge.objects.filter(
        level='global', 
        achievement_method='threshold',
        threshold_type='log_entries'
    ).exclude(threshold_value__isnull=True)  

    if active_trips:
        for badge in logentrybadges:
            for trip in active_trips:
                trippers = trip.trippers.all()
                logs.append(f"Found {trippers.count()} trippers for trip: {trip.name}")
                
                for tripper in trippers:
                    logentry_count = LogEntry.objects.filter(tripper=tripper).count()
                    
                    if logentry_count >= badge.threshold_value:
                        if not tripper.badges.filter(pk=badge.pk).exists(): 
                            tripper.badges.add(badge)
                            tripper.save()
                            BadgeAssignment.objects.create(tripper=tripper, badge=badge)
                            logs.append(f"Badge '{badge.name}' assigned to Tripper {tripper.name} due to writing {logentry_count} log entries.")
    else:
        logs.append(f"No Badges for logentries")

    # Assign badges for having an API key 
    # to be replaced by for having locations or photos
    logs.append(f"\n")
    logs.append(f"Assign Badges for Trippers with API key")
    api_key_badges = Badge.objects.filter(
        level='global', 
        achievement_method='threshold',
        threshold_type='tripper_has_api_key'
    ).exclude(threshold_value__isnull=True)  
    if active_trips:
        for api_key_badge in api_key_badges:
            for trip in active_trips:
                trippers = trip.trippers.all()
                logs.append(f"Checking API keys for {trippers.count()} trippers in trip: {trip.name}")
                
                for tripper in trippers:
                    if tripper.dawarich_api_key or tripper.immich_api_key:
                        if not tripper.badges.filter(pk=api_key_badge.pk).exists(): 
                            tripper.badges.add(api_key_badge)
                            tripper.save()
                            BadgeAssignment.objects.create(tripper=tripper, badge=api_key_badge)
                            logs.append(f"Badge '{api_key_badge.name}' assigned to Tripper {tripper.name} for having an API key.")
    else:
        logs.append(f"No badges for trippers with api keys")

    # Assign badges for being in multiple trips
    logs.append("\nAssign Badges for Trippers that went on multiple trips")

    multiple_trips_badges = Badge.objects.filter(
        level="global",
        achievement_method="threshold",
        threshold_type="trip_count"
    ).exclude(threshold_value__isnull=True)

    if multiple_trips_badges.exists():  
        trippers = Tripper.objects.annotate(trip_count=models.Count("trips")) 

        assignments = []  

        for tripper in trippers:
            for multiple_trips_badge in multiple_trips_badges:
                if tripper.trip_count >= multiple_trips_badge.threshold_value:
                    if not tripper.badges.filter(pk=multiple_trips_badge.pk).exists():
                        tripper.badges.add(multiple_trips_badge)
                        assignments.append(BadgeAssignment(tripper=tripper, badge=multiple_trips_badge))
                        logs.append(f"Badge '{multiple_trips_badge.name}' assigned to Tripper {tripper.name} for participating in {tripper.trip_count} trips.")

        if assignments:
            BadgeAssignment.objects.bulk_create(assignments)
    else:
        logs.append("No badges for multiple trips")

    logs.append(f"\nTask end")
    return "\n".join(logs)


if not Schedule.objects.filter(func='tripapp.tasks.assign_badges').exists():
    Schedule.objects.create(
        func='tripapp.tasks.assign_badges',
        schedule_type=Schedule.HOURLY,
        repeats=-1
    )



def fetch_locations_for_tripper():
    logs = []
    today = timezone.now()
    logs.append(f"Task start: {today}")
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    if not active_trips:
       logs.append(f"No active trips")

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

                        try:
                            current_lat = float(current_lat)
                            current_long = float(current_long)
                            aware_timestamp = make_aware(datetime.fromtimestamp(timestamp))
                        except (TypeError, ValueError) as e:
                            logs.append(f"Error processing point data: {e}")
                            continue

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
                                timestamp=aware_timestamp,
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
    today = timezone.now()
    logs.append(f"Task start: {today}")
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    if not active_trips:
       logs.append(f"No active trips")

    for trip in active_trips:
        for tripper in trip.trippers.all():
            last_photolocation = ImmichPhotos.objects.filter(tripper=tripper).order_by('-timestamp').first()
            start_date = last_photolocation.timestamp if last_photolocation else timezone.make_aware(datetime.combine(today, datetime.min.time()))
            # start_date from photolocation is in local datetime from last photo. 
            # add 1 milisecond?
            immich_start_date = start_date + timedelta(milliseconds=1)
            logs.append(f"Start date for {tripper.name}: {immich_start_date.isoformat()}")

            if tripper.immich_url:
                url = f"{tripper.immich_url}api/search/metadata"
                headers = {"x-api-key": tripper.immich_api_key}
                payload = {
                    "takenAfter": immich_start_date.isoformat(),
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
                    logs.append(str(item.get("id", "Unknown ID")))
                    logs.append(str(exif_info.get("latitude", "No Latitude")))

                    try:
                        lat = float(exif_info["latitude"]) if exif_info.get("latitude") is not None else None
                        long = float(exif_info["longitude"]) if exif_info.get("longitude") is not None else None
                    except (TypeError, ValueError) as e:
                        logs.append(f"Invalid latitude/longitude for {item['id']}: {e}")
                        continue

                    if lat is None or long is None:
                        logs.append(f"Skipping photo ID {item['id']} due to missing or invalid coordinates.")
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
                            local_datetime = datetime.fromisoformat(item['localDateTime'].replace("Z", "+00:00"))
                            ImmichPhotos.objects.create(
                                tripper=tripper,
                                immich_photo_id=item["id"],
                                latitude=lat,
                                longitude=long,
                                city=exif_info.get("city"),
                                timestamp=local_datetime,
                                thumbnail=ContentFile(thumbnail_response.content, file_name),
                            )
                            logs.append(f"Saving photo ID: {item['id']}, Latitude: {lat}, Longitude: {long} in localdatetime {local_datetime.isoformat()}")
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


def update_dayprogram_maps():
    logs = []
    today = timezone.now().date()
    relevant_dayprograms = DayProgram.objects.filter(tripdate__gte=today - timezone.timedelta(days=1))
    logs.append(f"Start generating static maps for {relevant_dayprograms.count()} relevant days")

    for dayprogram in relevant_dayprograms:
        logs.append(f"Generating map for DayProgram {dayprogram.id} on {dayprogram.tripdate}")
        generate_static_map(dayprogram)

    logs.append(f"End Generating")
    return "\n".join(logs)


if not Schedule.objects.filter(func='tripapp.tasks.update_dayprogram_maps').exists():
    Schedule.objects.create(
        func='tripapp.tasks.update_dayprogram_maps',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )


WEATHER_CODE_TO_EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️", 51: "🌦️", 53: "🌦️", 55: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️", 77: "🌨️",
    80: "🌧️", 81: "🌧️", 82: "🌧️",
    95: "⛈️", 96: "⛈️", 99: "⛈️"
}


def fetch_and_store_yesterdays_weather():
    logs = []
    yesterday = datetime.today() - timedelta(days=1)
    dayprograms = DayProgram.objects.filter(tripdate=yesterday)

    for dp in dayprograms:
        points = dp.points.all()
        if not points:
            continue

        avg_lat = sum(p.latitude for p in points) / len(points)
        avg_lon = sum(p.longitude for p in points) / len(points)

        temp_unit = settings.TEMPERATURE_UNIT.upper()
        temp_param = "&temperature_unit=fahrenheit" if temp_unit == 'F' else ""
        temp_symbol = "°F" if temp_unit == 'F' else "°C"

        url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={avg_lat}&longitude={avg_lon}"
            f"&daily=weather_code,precipitation_sum,temperature_2m_max,temperature_2m_min,sunrise,sunset"
            f"{temp_param}"
            f"&timezone=Europe%2FBerlin"
            f"&start_date={yesterday}&end_date={yesterday}"
        )

        try:
            response = requests.get(url)
            data = response.json()
            daily = data.get("daily", {})
            if not daily:
                continue

            dp.recorded_weather = daily

            code = daily["weather_code"][0]
            emoji = WEATHER_CODE_TO_EMOJI.get(code, "🌈")
            t_max = daily["temperature_2m_max"][0]
            t_min = daily["temperature_2m_min"][0]
            rain = daily["precipitation_sum"][0]
            sunrise = daily["sunrise"][0][-5:]
            sunset = daily["sunset"][0][-5:]

            description = (
                f"{emoji} On {yesterday.strftime('%-d %B')} we had this weather:\n"
                f"🌡️ Max: {t_max}{temp_symbol}, Min: {t_min}{temp_symbol}\n"
                f"💧 {rain} mm\n"
                f"🌅 Sunrise: {sunrise} – 🌇 Sunset: {sunset}"
            )

            dp.recorded_weather_text = description
            dp.save()
            logs.append(f"Weather recorded for {dp.tripdate}")
        except Exception as e:
            logs.append(f"Error retrieving weather for {dp.tripdate}: {e}")


if not Schedule.objects.filter(func='tripapp.tasks.fetch_and_store_yesterdays_weather').exists():
    Schedule.objects.create(
        func='tripapp.tasks.fetch_and_store_yesterdays_weather',
        schedule_type=Schedule.DAILY,
        repeats=-1
    )

