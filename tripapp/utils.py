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

from requests.exceptions import RequestException
from django.core.cache import cache


logger = logging.getLogger(__name__)


UNSPLASH_ACCESS_KEY = settings.UNSPLASH_ACCESS_KEY
UNSPLASH_CACHE_KEY = "unsplash_random_roadtrip"
UNSPLASH_CACHE_TIMEOUT = 3600  


def get_random_unsplash_image(category):

    cached_url = cache.get(UNSPLASH_CACHE_KEY)
    if cached_url:
        return cached_url

    url = 'https://api.unsplash.com/photos/random'
    params = {
        'client_id': UNSPLASH_ACCESS_KEY,
        'query': category,
        'orientation': 'landscape',
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        photo_url = data.get("urls", {}).get("regular")
        if photo_url:
            cache.set(UNSPLASH_CACHE_KEY, photo_url, UNSPLASH_CACHE_TIMEOUT)
            return photo_url
    except RequestException:
        pass

    return "/static/default_roadtrip.jpg"


def simplify_locations(locations, epsilon=0.0005):
    coords = [(loc.latitude, loc.longitude) for loc in locations]
    return rdp(coords, epsilon=epsilon)

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


def generate_static_map_for_trip(trip):
    staticmaps_url = settings.STATICMAPS_URL
    staticmaps_api_key = settings.STATICMAPS_API_KEY

    if not staticmaps_url:
        logger.info("Staticmaps not configured.")
        return None

    map_dir = os.path.join(settings.MEDIA_ROOT, "trip_maps")
    os.makedirs(map_dir, exist_ok=True)

    markers = []


    dayprograms = trip.dayprograms.all().order_by('dayprogramnumber')

    for dp in dayprograms:
        for point in dp.points.all():
            markers.append(f"{point.latitude},{point.longitude}")


    # Staticmap parameters
    params = {
        "width": 1000,
        "height": 700,
        "format": "png",
    }

    query_parts = []

    if markers:
        marker_param = f"markers=width:20|height:20|{'|'.join(markers)}"
        query_parts.append(marker_param)

    base_url = f"{staticmaps_url}?{'&'.join(query_parts)}"

    if staticmaps_api_key:
        request_url = f"{base_url}&api_key={staticmaps_api_key}"
    else:
        request_url = base_url

    logger.info(f"StaticTripMap URL: {request_url}")

    response = requests.get(request_url)
    if response.status_code != 200:
        return None
    
    folder = os.path.join(settings.MEDIA_ROOT, "trip_maps")
    os.makedirs(folder, exist_ok=True)

    filename = f"{trip.slug}.png"
    filepath = os.path.join(folder, filename)

    with open(filepath, "wb") as f:
        f.write(response.content)

    return filepath



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


def get_country_coords(country_code):
    cache_key = f"country_coords_{country_code}"
    coords = cache.get(cache_key)
    if coords:
        return coords

    url = f"https://nominatim.openstreetmap.org/search?country={country_code}&format=json&limit=1"
    response = requests.get(url, headers={'User-Agent': 'trip-planner-app'})

    if response.status_code == 200:
        data = response.json()
        if data:
            coords = float(data[0]['lat']), float(data[0]['lon'])
            cache.set(cache_key, coords, timeout=86400)
            return coords

    return None

from django_select2.forms import Select2MultipleWidget
import pycountry

def country_choices():
    return sorted(
        [(c.alpha_2, c.name) for c in pycountry.countries],
        key=lambda x: x[1]
    )