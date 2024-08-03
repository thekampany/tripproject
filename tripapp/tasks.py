# tasks.py

from django.utils import timezone
from django_q.tasks import schedule, Schedule
from .models import Badge, Tripper, BadgeAssignment, Trip
#import logging

#logger = logging.getLogger(__name__)


def assign_badges():
    #print("Assign badges task started.")
    today = timezone.now().date()
    badges = Badge.objects.filter(assignment_date=today)
    #print(f"Found {badges.count()} badges to assign.")

    # Haal alle trips op die actief zijn op vandaag
    active_trips = Trip.objects.filter(date_from__lte=today, date_to__gte=today)

    for badge in badges:
        trippers = Tripper.objects.all()

        # Voor elke actieve trip, krijg de trippers en maak BadgeAssignments aan
        for trip in active_trips:
            trippers = trip.trippers.all()
            print(f"Found {trippers.count()} trippers for trip: {trip.name}")
            for tripper in trippers:
                # Voeg de badge toe aan de tripper
                tripper.badges.add(badge)
                tripper.save()
                # Maak een BadgeAssignment aan
                BadgeAssignment.objects.create(tripper=tripper, badge=badge, trip=trip)
                print(f"Badge {badge.name} assigned to Tripper {tripper.name} for Trip {trip.name}.")



# Plan de taak om dagelijks te draaien
schedule(
    'tripapp.tasks.assign_badges',
    schedule_type=Schedule.DAILY,
    repeats=-1
)
