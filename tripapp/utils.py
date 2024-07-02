import requests
from django.conf import settings

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
