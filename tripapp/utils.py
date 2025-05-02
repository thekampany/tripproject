import requests
import os
from django.conf import settings
from django.core.files.base import ContentFile
import logging
from tripapp.models import Location
import numpy as np
from rdp import rdp
import gpxpy

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