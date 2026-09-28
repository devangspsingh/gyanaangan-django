import logging
from urllib.parse import urlparse
from django.core.management.base import BaseCommand
from django.db.models import Count
from tracking.models import Event
from blog.models import BlogPost

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Syncs BlogPost.view_count from recorded tracking.Event page_view data"

    def handle(self, *args, **options):
        self.stdout.write("Calculating blog views from tracking.Event table...")

        # Aggregate events by URL
        counts_by_url = (
            Event.objects.filter(url__icontains="/blog/")
            .values("url")
            .annotate(views=Count("id"))
        )

        slug_views = {}
        for item in counts_by_url:
            url = item.get("url") or ""
            path = urlparse(url).path
            if path.startswith("/blog/"):
                parts = path.strip("/").split("/")
                if len(parts) >= 2 and parts[0] == "blog":
                    slug = parts[1]
                    slug_views[slug] = slug_views.get(slug, 0) + item["views"]

        updated_count = 0
        for slug, views in slug_views.items():
            updated = BlogPost.objects.filter(slug=slug).update(view_count=views)
            if updated:
                updated_count += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully synced view counts for {updated_count} blog posts (Total unique slugs with views: {len(slug_views)})."
            )
        )
