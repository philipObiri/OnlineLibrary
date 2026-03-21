"""
Management command: generate_thumbnails
Generates cover images for publications that have a PDF but no cover_image,
using PyMuPDF (fitz) to render the first page.

Usage:
    python manage.py generate_thumbnails
    python manage.py generate_thumbnails --force   # regenerate all covers
"""
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from library.models import Publication


class Command(BaseCommand):
    help = 'Generate cover image thumbnails from PDF first pages using PyMuPDF'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Regenerate covers even if cover_image already exists',
        )

    def handle(self, *args, **options):
        try:
            import fitz  # PyMuPDF
        except ImportError:
            self.stderr.write(self.style.ERROR(
                'PyMuPDF is not installed. Run: pip install pymupdf'
            ))
            return

        covers_dir = Path(settings.MEDIA_ROOT) / 'covers'
        covers_dir.mkdir(parents=True, exist_ok=True)

        qs = Publication.objects.filter(is_published=True)
        if not options['force']:
            qs = qs.filter(cover_image='')

        total = qs.count()
        if total == 0:
            self.stdout.write('No publications need thumbnails.')
            return

        self.stdout.write(f'[IMG]  Generating thumbnails for {total} publications...\n')
        success, skipped, errors = 0, 0, 0

        for pub in qs.iterator():
            if not pub.file:
                skipped += 1
                continue

            # Resolve absolute path of the PDF
            pdf_path = Path(settings.MEDIA_ROOT) / str(pub.file)
            if not pdf_path.exists():
                self.stderr.write(f'   [WARN]  File not found: {pdf_path}')
                skipped += 1
                continue

            cover_filename = f'{pub.slug}.jpg'
            cover_path = covers_dir / cover_filename

            try:
                doc = fitz.open(str(pdf_path))
                page = doc[0]
                # 0.6x zoom → ~360×510 px — sufficient for catalogue cards, fast to load
                mat = fitz.Matrix(0.6, 0.6)
                pix = page.get_pixmap(matrix=mat)
                # Save as JPEG at quality 75 (sharp enough, ~5–15 KB per cover)
                pix.save(str(cover_path), jpg_quality=75)
                doc.close()

                pub.cover_image = f'covers/{cover_filename}'
                pub.save(update_fields=['cover_image'])
                success += 1
                self.stdout.write(f'   [OK] {pub.title[:60]}')

            except Exception as e:
                self.stderr.write(f'   [ERR] Error on "{pub.title[:50]}": {e}')
                errors += 1

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'\n[DONE] Done! [OK] {success} generated  [WARN]  {skipped} skipped  [ERR] {errors} errors\n'
        ))
