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
                # No PDF — generate a styled placeholder cover with Pillow
                cover_filename = f'{pub.slug}.jpg'
                cover_path = covers_dir / cover_filename
                if not cover_path.exists() or options['force']:
                    try:
                        from PIL import Image, ImageDraw, ImageFont
                        PALETTE = [
                            (0x1B, 0x3A, 0x6B), (0x2D, 0x5F, 0x8A), (0xC9, 0xA8, 0x4C),
                            (0x2E, 0x7D, 0x32), (0x6A, 0x1B, 0x9A), (0xC6, 0x28, 0x28), (0x00, 0x69, 0x5C),
                        ]
                        bg = PALETTE[pub.pk % len(PALETTE)]
                        W, H = 300, 420
                        img = Image.new("RGB", (W, H), bg)
                        draw = ImageDraw.Draw(img)
                        draw.rectangle([14, 14, W - 15, H - 15], outline=(255, 255, 255), width=1)
                        words = pub.title.split()
                        initials = (words[0][0] + (words[1][0] if len(words) > 1 else '')).upper()
                        try:
                            font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 110)
                            font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
                        except OSError:
                            font_big = ImageFont.load_default()
                            font_sm  = ImageFont.load_default()
                        bbox = draw.textbbox((0, 0), initials, font=font_big)
                        tw = bbox[2] - bbox[0]
                        draw.text(((W - tw) // 2, 140), initials, font=font_big, fill=(255, 255, 255, 40))
                        label = pub.get_publication_type_display().upper()
                        bbox2 = draw.textbbox((0, 0), label, font=font_sm)
                        lw = bbox2[2] - bbox2[0]
                        draw.text(((W - lw) // 2, 340), label, font=font_sm, fill=(255, 255, 255, 140))
                        accent = tuple(min(255, c + 40) for c in bg)
                        draw.rectangle([0, H - 6, W, H], fill=accent)
                        img.save(str(cover_path), "JPEG", quality=80)
                        pub.cover_image = f'covers/{cover_filename}'
                        pub.save(update_fields=['cover_image'])
                        success += 1
                        self.stdout.write(f'   [PLACEHOLDER] {pub.title[:60]}')
                    except Exception as e:
                        self.stderr.write(f'   [ERR] Placeholder failed for "{pub.title[:50]}": {e}')
                        errors += 1
                else:
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
