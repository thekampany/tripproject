import json
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import IntegrityError, transaction

class Command(BaseCommand):
    help = 'Load fixtures, ignoring duplicate contenttypes'

    def handle(self, *args, **kwargs):
        try:
            with transaction.atomic():
                call_command('loaddata', 'db.json')
        except IntegrityError as e:
            self.stdout.write(self.style.WARNING(f'IntegrityError: {e}'))
            self.stdout.write(self.style.WARNING('Ignoring duplicate contenttypes and continuing...'))

            with open('db.json') as f:
                fixtures = json.load(f)

            filtered_fixtures = [obj for obj in fixtures if obj['model'] != 'contenttypes.contenttype']

            with open('filtered_db.json', 'w') as f:
                json.dump(filtered_fixtures, f)

            call_command('loaddata', 'filtered_db.json')
