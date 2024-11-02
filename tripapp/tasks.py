# tasks.py

from django.utils import timezone
from django_q.tasks import schedule, Schedule
from .models import Badge, Tripper, BadgeAssignment, Trip, Location
import requests
from datetime import datetime, timezone
#import logging

#logger = logging.getLogger(__name__)


def assign_badges():
    #print("Assign badges task started.")
    today = timezone.now().date()
    badges = Badge.objects.filter(assignment_date=today)
    #print(f"Found {badges.count()} badges to assign.")

    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    for badge in badges:
        trippers = Tripper.objects.all()

        for trip in active_trips:
            trippers = trip.trippers.all()
            print(f"Found {trippers.count()} trippers for trip: {trip.name}")
            for tripper in trippers:
                tripper.badges.add(badge)
                tripper.save()
                BadgeAssignment.objects.create(tripper=tripper, badge=badge, trip=trip)
                print(f"Badge {badge.name} assigned to Tripper {tripper.name} for Trip {trip.name}.")



schedule(
    'tripapp.tasks.assign_badges',
    schedule_type=Schedule.DAILY,
    repeats=-1
)



def fetch_locations_for_tripper():

    today = datetime.now(timezone.utc)
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)
    for trip in active_trips:
        trippers = trip.trippers.all()
 
        for tripper in trippers:

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
                    timestamp=datetime.fromtimestamp(point['timestamp'], tz=timezone.utc)
                  )

Schedule.objects.create(
        func='app.tasks.fetch_locations_for_tripper',  
        schedule_type=Schedule.DAILY,  
        repeats=-1,  
    )