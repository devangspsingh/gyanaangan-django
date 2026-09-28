from django.core.management.base import BaseCommand
from tracking.sync_service import sync_tracking_analytics


class Command(BaseCommand):
    help = "Incrementally syncs unprocessed tracking.Event records into BlogAnalytics and ResourceAnalytics models"

    def handle(self, *args, **options):
        self.stdout.write("Starting incremental tracking analytics sync...")
        results = sync_tracking_analytics()

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Sync complete! Processed {results['processed_events']:,} events in {results['duration_seconds']}s. "
                f"Updated {results['updated_blogs']} blog records, {results['updated_resources']} resource records."
            )
        )
