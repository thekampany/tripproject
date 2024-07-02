# tasks.py

from django.utils import timezone
from django_q.tasks import schedule, Schedule
from .models import Badge, Tripper
import logging

logger = logging.getLogger(__name__)


def assign_badges():
    today = timezone.now().date()
    badges = Badge.objects.filter(assignment_date=today)
    for badge in badges:
        trippers = Tripper.objects.all()
        for tripper in trippers:
            tripper.badges.add(badge)
            tripper.save()
            logger.info(f"Badge {badge.name} assigned to Tripper {tripper.name}")

# Plan de taak om dagelijks te draaien
schedule(
    'tripapp.tasks.assign_badges',
    schedule_type=Schedule.DAILY,
    repeats=-1
)
