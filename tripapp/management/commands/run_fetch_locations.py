from django.core.management.base import BaseCommand
from tripapp.tasks import fetch_locations_for_tripper

class Command(BaseCommand):
    help = 'Fetch locations for all trippers'

    def handle(self, *args, **kwargs):
        self.stdout.write("Running fetch_locations_for_tripper task...")
        fetch_locations_for_tripper()
        self.stdout.write("Task completed.")
