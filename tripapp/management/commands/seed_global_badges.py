from django.core.management.base import BaseCommand
from tripapp.models import Badge

class Command(BaseCommand):
    help = 'Seed global badges'

    def handle(self, *args, **options):
        global_badges = [
            {"name": "BingoBopper3", "image": "badges/bingobopper3.png", "threshold_value":"3", "threshold_type":"bingo_answer_uploads"},
            {"name": "BingoBopper10", "image": "badges/bingobopper10.png", "threshold_value":"10", "threshold_type":"bingo_answer_uploads"},
            {"name": "BingoBopper20", "image": "badges/bingobopper20.png", "threshold_value":"20", "threshold_type":"bingo_answer_uploads"},
            {"name": "PlanesTrainsnBlogtypos3", "image": "badges/planestrainsnblogtypos3.png", "threshold_value":"3", "threshold_type":"log_entries"},
            {"name": "PlanesTrainsnBlogtypos10", "image": "badges/planestrainsnblogtypos10.png", "threshold_value":"10", "threshold_type":"log_entries"},
            {"name": "PlanesTrainsnBlogtypos20", "image": "badges/planestrainsnblogtypos20.png", "threshold_value":"20", "threshold_type":"log_entries"},
            {"name": "Two Tripper", "image": "badges/twotripper.png", "threshold_value":"2", "threshold_type":"trip_count"},
            {"name": "Three Tripper", "image": "badges/threetripper.png", "threshold_value":"3", "threshold_type":"trip_count"},
            {"name": "Ten Tripper", "image": "badges/tentripper.png", "threshold_value":"10", "threshold_type":"trip_count"},
            {"name": "Twenty Tripper", "image": "badges/twentytripper.png", "threshold_value":"20", "threshold_type":"trip_count"},
            {"name": "Track the Tripper", "image": "badges/trackthetripper.png", "threshold_value":"1", "threshold_type":"tripper_has_api_key"},
            {"name": "My Log got 3 likes", "image": "badges/like3.png", "threshold_value":"3", "threshold_type":"log_likes"},
            {"name": "My Log got 10 likes", "image": "badges/like10.png", "threshold_value":"10", "threshold_type":"log_likes"},
        ]

        for badge_data in global_badges:
            badge, created = Badge.objects.get_or_create(
                name=badge_data["name"],
                defaults={
                    "achievement_method": "threshold",
                    "level": "global",
                    "image": badge_data["image"],
                    "threshold_value": badge_data["threshold_value"],
                    "threshold_type": badge_data["threshold_type"],
                },
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created badge: {badge.name}"))
            else:
                self.stdout.write(f"Badge {badge.name} already exists.")
