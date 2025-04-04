import requests
import os
from django.conf import settings
from django.core.files.base import ContentFile
import logging
from tripapp.models import Location

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


def generate_static_map(dayprogram):
    staticmaps_url = settings.STATICMAPS_URL
    if not staticmaps_url:
        logger.info(f"No staticmaps url {staticmaps_url}")
        return  

    markers = []
    polylines = []

    if dayprogram.points.exists():
        logger.info(f"Points")
        for point in dayprogram.points.all():
            markers.append(f"{point.latitude},{point.longitude}")

    tripdate = dayprogram.tripdate
    logger.info(f"Dayprogram tripdate {tripdate} ")
    locations = Location.objects.filter(timestamp__date=tripdate)

    if locations.exists():
        polyline = "|".join([f"{loc.latitude},{loc.longitude}" for loc in date.locations.all()])
        polylines.append((polyline, "0000FF", "weight:6"))

    #routes to be added

    params = {
        "width": 800,
        "height": 600,
        "format": "png",
    }

    if markers:
        params["markers"] = f"markers=width:28|height:28|{'|'.join(markers)}"

    if polylines:
        params["polyline"] = [
            f"polyline=weight:6|color:{color}|{coords}" for coords, color, *_ in polylines
        ]

    request_url = f"{staticmaps_url}?{'&'.join(params.get('polyline', []) + [params['markers']] if markers else [])}"
    logger.info(f"{request_url}")
    response = requests.get(request_url)
    if response.status_code == 200:
        filename = f"map_dayprogram_{dayprogram.id}.png"
        dayprogram.map_image.save(filename, ContentFile(response.content))
        dayprogram.save()