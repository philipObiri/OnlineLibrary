"""
Management command: delete_online_resources
Deletes all publications imported from online sources (OpenAlex, DOAJ, arXiv).
Identified by their source tags: source:openalex, source:doaj, source:arxiv.

Usage:
    python manage.py delete_online_resources
    python manage.py delete_online_resources --source doaj
    python manage.py delete_online_resources --source arxiv
    python manage.py delete_online_resources --dry-run
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from library.models import Publication

SOURCE_TAGS = {
    "openAlex": "source:openalex",
    "doaj":     "source:doaj",
    "arxiv":    "source:arxiv",
}


class Command(BaseCommand):
    help = "Delete publications imported from online sources (OpenAlex, DOAJ, arXiv)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=list(SOURCE_TAGS.keys()) + ["all"],
            default="all",
            help="Which source to delete (default: all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        dry_run = options["dry_run"]

        # Build list of tags to target
        if source == "all":
            tags = list(SOURCE_TAGS.values())
        else:
            tags = [SOURCE_TAGS[source]]

        # Collect matching publications (union across selected tags)
        qs = Publication.objects.filter(tags__name__in=tags).distinct()
        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.WARNING("No online-sourced publications found."))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(f"--- DRY RUN — nothing will be deleted ---\n"))
            for pub in qs.order_by("publication_type", "title"):
                tag_names = ", ".join(t.name for t in pub.tags.filter(name__in=tags))
                self.stdout.write(f"  [{tag_names}] {pub.title[:90]}")
            self.stdout.write(f"\nWould delete {total} publication(s).")
            return

        # Confirm before deleting
        self.stdout.write(
            self.style.WARNING(
                f"\nAbout to permanently delete {total} publication(s) "
                f"from: {', '.join(tags)}\n"
            )
        )
        confirm = input("Type 'yes' to confirm: ").strip().lower()
        if confirm != "yes":
            self.stdout.write("Aborted.")
            return

        # Delete associated cover image files from disk (placeholder JPEGs)
        covers_deleted = 0
        for pub in qs:
            if pub.cover_image:
                cover_path = Path(settings.MEDIA_ROOT) / str(pub.cover_image)
                if cover_path.exists():
                    try:
                        cover_path.unlink()
                        covers_deleted += 1
                    except OSError:
                        pass

        # Delete the database records
        deleted_count, _ = qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDeleted {deleted_count} publication(s) "
                f"and {covers_deleted} cover image file(s)."
            )
        )
