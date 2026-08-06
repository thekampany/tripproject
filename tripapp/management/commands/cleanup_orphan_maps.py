import os
from django.conf import settings
from django.core.management.base import BaseCommand
from tripapp.models import DayProgram  


class Command(BaseCommand):
    help = "Remove map images on disk (media/maps/) no longer referenced in DayProgram"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show files to be deleted without deleting.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        maps_dir = os.path.join(settings.MEDIA_ROOT, "maps")

        if not os.path.isdir(maps_dir):
            self.stdout.write(self.style.ERROR(f"Map not found: {maps_dir}"))
            return

        referenced_names = set(
            DayProgram.objects.exclude(map_image="")
            .exclude(map_image__isnull=True)
            .values_list("map_image", flat=True)
        )
        referenced_filenames = {os.path.basename(name) for name in referenced_names}

        self.stdout.write(f"Number of referenced map-images in database: {len(referenced_filenames)}")

        all_files = [
            f for f in os.listdir(maps_dir)
            if os.path.isfile(os.path.join(maps_dir, f))
        ]
        self.stdout.write(f"Number of files on disk: {len(all_files)}")

        orphans = [f for f in all_files if f not in referenced_filenames]

        if not orphans:
            self.stdout.write(self.style.SUCCESS("No orphan-files found."))
            return

        self.stdout.write(self.style.WARNING(f"Found orphan-files: {len(orphans)}"))

        total_size = 0
        for fname in sorted(orphans):
            full_path = os.path.join(maps_dir, fname)
            size = os.path.getsize(full_path)
            total_size += size
            self.stdout.write(f"  {'[DRY RUN] ' if dry_run else ''}{full_path} ({size} bytes)")
            if not dry_run:
                try:
                    os.remove(full_path)
                except OSError as e:
                    self.stdout.write(self.style.ERROR(f"    Could not remove: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would delete' if dry_run else 'Deleted'}: {len(orphans)} files, "
                f"total {total_size / (1024 * 1024):.2f} MB"
            )
        )