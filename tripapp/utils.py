import requests
import os
from django.conf import settings
from django.core.files.base import ContentFile
import logging
from rdp import rdp
import gpxpy

import datetime
from django.utils.text import slugify
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

from tripapp.models import Trip, DayProgram, Point, Tripper, Location
from django.db import models

from requests.exceptions import RequestException
from django.core.cache import cache


geolocator = Nominatim(user_agent="tripapp")

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
        logger.info("No staticmaps url configured.")  
        return  
    
    markers = []
    polyline_params = []

    if dayprogram.points.exists():
        logger.info("Processing points for markers.") 
        for point in dayprogram.points.all():
            markers.append(f"{point.latitude},{point.longitude}")

    tripdate = dayprogram.tripdate
    logger.info("Processing dayprogram for date: %s", tripdate)

    locations = list(Location.objects.filter(timestamp__date=tripdate))

    if locations:
        logger.info("Found %d locations for polyline.", len(locations))
        
        coords = [(loc.latitude, loc.longitude) for loc in locations]

        if len(coords) > 150:
            simplified = rdp(coords, epsilon=0.0005)
            logger.info("Reduced from %d to %d points using RDP.", len(coords), len(simplified))
        else:
            simplified = coords        
                
        polyline_str = "|".join([f"{lat},{lon}" for lat, lon in simplified])
        polyline_params.append(f"polyline=weight:4|color:0000FF|{polyline_str}") 

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
                    coords = list(gpx_points)
                    simplified = rdp(coords, epsilon=0.0005) if len(coords) > 150 else coords
                    polyline_str = "|".join(f"{lat},{lon}" for lat, lon in simplified)
                    polyline_params.append(
                        f"polyline=weight:2|color:blue|strokeDasharray:10,15|{polyline_str}"
                    )

    marker_param = None
    if markers:
        marker_param = f"markers=width:20|height:20|{'|'.join(markers)}"

    query_parts = polyline_params[:] 
    if marker_param:
        query_parts.append(marker_param)

    base_url = f"{staticmaps_url}?{'&'.join(query_parts)}"
    logger.info("Requesting static map (without api_key): %s", base_url)

    request_url = f"{base_url}&api_key={staticmaps_api_key}" if staticmaps_api_key else base_url

    response = requests.get(request_url)
    if response.status_code == 200:
        filename = f"map_dayprogram_{dayprogram.id}.png"
        dayprogram.map_image.save(filename, ContentFile(response.content)) 
        dayprogram.save()
    else:
        logger.warning("Static map request failed with status %d", response.status_code)

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

    params = {
        "width": 1000,
        "height": 700,
        "format": "png",
    }

    query_parts = []
    if markers:
        query_parts.append(f"markers=width:20|height:20|{'|'.join(markers)}")

    base_url = f"{staticmaps_url}?{'&'.join(query_parts)}"
    logger.info(f"StaticTripMap URL: {base_url}") 

    if staticmaps_api_key:
        request_url = f"{base_url}&api_key={staticmaps_api_key}"
    else:
        request_url = base_url

    response = requests.get(request_url)
    if response.status_code != 200:
        logger.warning(f"Staticmap request failed with status {response.status_code}")
        return None

    filename = f"{trip.slug}.png"
    filepath = os.path.join(map_dir, filename)
    with open(filepath, "wb") as f:
        f.write(response.content) 

    return filepath


def create_trip_from_itinerary(itinerary, tribe, start_date,user):
    geolocator = Nominatim(user_agent="trippanion")

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
            logger.warning("Error geocoding (%.1f, %.1f): %s", lat, lon, e)

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

    location = geolocator.geocode({"country": country_code}, language="en", timeout=5)
    if location:
        coords = (location.latitude, location.longitude)
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

def country_code_to_name(code: str):
    if not isinstance(code, str) or not code.strip():
        return []

    countrylist = []
    countries = code.split(",")

    for countrycode in countries:
        countrycode = countrycode.strip().upper()

        if len(countrycode) == 2:
            country = pycountry.countries.get(alpha_2=countrycode)
            if country:
                countrylist.append(country.name)

    return countrylist

def reverse_geocode_area(latitude, longitude) -> str:
    try:
        geolocator = Nominatim(user_agent="tripapp")
        location   = geolocator.reverse((latitude, longitude), language="en", timeout=5)
        if not location:
            return f"{latitude:.2f}, {longitude:.2f}"
        
        address = location.raw.get("address", {})
        area = (
            address.get("village") or
            address.get("town") or
            address.get("city") or
            address.get("county") or
            address.get("state") or
            address.get("country") or
            location.address
        )
        return area
    except GeocoderTimedOut:
        return f"{latitude:.2f}, {longitude:.2f}"


from math import radians, sin, cos, sqrt, atan2
from django.db.models import Q
from datetime import date

def haversine(lat1, lon1, lat2, lon2):
    R = 6371  

    lat1, lon1, lat2, lon2 = map(radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def distance_per_day(tripper, day: date) -> float:
    locations = (
        Location.objects
        .filter(tripper=tripper, timestamp__date=day)
        .order_by('timestamp')
        .values_list('latitude', 'longitude')
    )

    total_km = 0.0
    points = list(locations)

    for i in range(len(points) - 1):
        lat1, lon1 = points[i]
        lat2, lon2 = points[i + 1]
        total_km += haversine(lat1, lon1, lat2, lon2)

    return round(total_km, 2)