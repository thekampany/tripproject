import requests
import os
from django.conf import settings
from django.core.files.base import ContentFile
import logging
from tripapp.models import Location
import numpy as np
from rdp import rdp
import gpxpy

import datetime
from django.utils.text import slugify
from geopy.geocoders import Nominatim
from tripapp.models import Trip, DayProgram, Point, Tripper
from django.db import models



logger = logging.getLogger(__name__)


UNSPLASH_ACCESS_KEY = settings.UNSPLASH_ACCESS_KEY


def get_random_unsplash_image(category):
    url = 'https://api.unsplash.com/photos/random'
    params = {
        'client_id': UNSPLASH_ACCESS_KEY,
        'query': category,
        'orientation': 'landscape',
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data['urls']['regular']
    else:
        return None



def simplify_locations(locations, epsilon=0.0005):
    coords = np.array([[loc.latitude, loc.longitude] for loc in locations])
    simplified = rdp(coords, epsilon=epsilon)
    return simplified 



def generate_static_map(dayprogram):
    staticmaps_url = settings.STATICMAPS_URL
    staticmaps_api_key = settings.STATICMAPS_API_KEY

    if not staticmaps_url:
        logger.info(f"No staticmaps url {staticmaps_url}")
        return  
    
    markers = []
    polyline_params = []

    if dayprogram.points.exists():
        logger.info(f"Points")
        for point in dayprogram.points.all():
            markers.append(f"{point.latitude},{point.longitude}")

    tripdate = dayprogram.tripdate
    logger.info(f"Dayprogram tripdate {tripdate} ")

    locations = list(Location.objects.filter(timestamp__date=tripdate))

    if locations:
        logger.info(f"Found {len(locations)} locations for polyline.")
        
        coords = np.array([[loc.latitude, loc.longitude] for loc in locations])
        if len(coords) > 150:
            simplified = rdp(coords, epsilon=0.0005)
            logger.info(f"Reduced from {len(coords)} to {len(simplified)} points using RDP.")
        else:
            simplified = coords
        
        polyline_str = "|".join([f"{lat},{lon}" for lat, lon in simplified])
        polyline_params.append(f"polyline=weight:4|color:0000FF|{polyline_str}") 


    routes = dayprogram.routes.all()
    for route in dayprogram.routes.all():
        if route.gpx_file:
            with route.gpx_file.open("r") as f:
                gpx_data = f.read()
                gpx = gpxpy.parse(gpx_data)
                gpx_points = []
                for track in gpx.tracks:
                    for segment in track.segments:
                        for point in segment.points:
                            gpx_points.append([point.latitude, point.longitude])
                    
                if gpx_points:
                    coords = np.array(gpx_points)
                    if len(coords) > 150:
                        simplified = rdp(coords, epsilon=0.0005)
                    else:
                        simplified = coords
                    polyline_str = "|".join([f"{lat},{lon}" for lat, lon in simplified])
                    polyline_params.append(f"polyline=weight:4|color:FF0000|{polyline_str}")  

    params = {
        "width": 800,
        "height": 600,
        "format": "png",
    }
    marker_param = None
    if markers:
        marker_param = f"markers=width:20|height:20|{'|'.join(markers)}"

    query_parts = polyline_params
    if marker_param:
        query_parts.append(marker_param)

    base_url = f"{staticmaps_url}?{'&'.join(query_parts)}"

    if staticmaps_api_key:
        request_url = f"{base_url}&api_key={staticmaps_api_key}"
    else:
        request_url = base_url

    logger.info(f"{request_url}")
    response = requests.get(request_url)
    if response.status_code == 200:
        filename = f"map_dayprogram_{dayprogram.id}.png"
        dayprogram.map_image.save(filename, ContentFile(response.content))
        dayprogram.save()




def create_trip_from_itinerary(itinerary, tribe, start_date,user):
    geolocator = Nominatim(user_agent="my_trip_app")

    all_locations = []
    for day in itinerary.itineraryidea_days.all():
        for loc in day.day_locations.all():
            all_locations.append((loc.latitude, loc.longitude))
        if getattr(day, "overnightlocation", None):
            o = day.overnightlocation
            all_locations.append((o.latitude, o.longitude))

    countries = set()
    for lat, lon in all_locations:
        try:
            location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
            if location and "country_code" in location.raw["address"]:
                countries.add(location.raw["address"]["country_code"].upper())
        except Exception as e:
            print(f"Error geocoding {lat},{lon}: {e}")

    country_codes = ",".join(sorted(countries))

    max_day = itinerary.itineraryidea_days.all().aggregate(models.Max("day_sequence"))["day_sequence__max"] or 1
    date_to = start_date + datetime.timedelta(days=max_day - 1)

    trip = Trip.objects.create(
        tribe=tribe,
        name=itinerary.name,
        description=itinerary.name,
        slug=slugify(itinerary.name),
        date_from=start_date,
        date_to=date_to,
        country_codes=country_codes,
    )

    # Ensure the logged-in user is also a Tripper for this trip
    tripper, created = Tripper.objects.get_or_create(user=user, defaults={'name': user.username})
    tripper.trips.add(trip)
    tripper.is_trip_admin = True
    tripper.save()


    for day in itinerary.itineraryidea_days.all().order_by("day_sequence"):
        tripdate = start_date + datetime.timedelta(days=day.day_sequence - 1)

        dayprogram = DayProgram.objects.create(
            trip=trip,
            description=day.day_description or f"Day {day.day_sequence}",
            tripdate=tripdate,
            dayprogramnumber=day.day_sequence,
            overnight_location=getattr(day.overnightlocation, "description", None)
            if getattr(day, "overnightlocation", None)
            else None,
        )

        for loc in day.day_locations.all().order_by("sequence"):
            point = Point.objects.create(
                name=loc.description or f"Point {loc.sequence}",
                latitude=loc.latitude,
                longitude=loc.longitude,
                trip=trip,
            )
            point.dayprograms.add(dayprogram)

        if getattr(day, "overnightlocation", None):
            o = day.overnightlocation
            point = Point.objects.create(
                name=o.description or "Overnight location",
                latitude=o.latitude,
                longitude=o.longitude,
                trip=trip,
                marker_type="bed",
            )
            point.dayprograms.add(dayprogram)

    return trip
