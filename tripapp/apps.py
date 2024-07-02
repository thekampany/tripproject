from django.apps import AppConfig


class TripappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tripapp'

    def ready(self):
        import tripapp.signals
