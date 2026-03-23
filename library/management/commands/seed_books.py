"""
Management command: seed_books
Seeds the database with real PhD textbooks from the 'Phd Books for E-library' directory.
Deduplicates books that appear in multiple courses — one record per unique title,
tagged with all semesters/courses it belongs to.

Usage:
    python manage.py seed_books
    python manage.py seed_books --books-dir "path/to/Phd Books for E-library"
"""
import os
import re
import shutil
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import get_user_model
from library.models import Category, Publication

User = get_user_model()

# ── Category definitions ─────────────────────────────────────────────────────

CATEGORIES = [
    {
        "name": "Research Methods",
        "icon": "bi-search",
        "color": "#1B3A6B",
        "description": "Quantitative and qualitative research methods, philosophy, and design.",
    },
    {
        "name": "Business Administration",
        "icon": "bi-building",
        "color": "#2D5F8A",
        "description": "Foundations of business administration, organisation theory, and management.",
    },
    {
        "name": "Finance & Accounting",
        "icon": "bi-cash-stack",
        "color": "#00695C",
        "description": "Financial systems, management accounting, markets, and risk theory.",
    },
    {
        "name": "Human Resource Management",
        "icon": "bi-people-fill",
        "color": "#C9A84C",
        "description": "Strategic HRM, organisational behaviour, and human capital development.",
    },
    {
        "name": "Marketing Management",
        "icon": "bi-megaphone-fill",
        "color": "#6A1B9A",
        "description": "Consumer behaviour, digital marketing, and market system dynamics.",
    },
    {
        "name": "Strategic Management & Leadership",
        "icon": "bi-trophy-fill",
        "color": "#1565C0",
        "description": "Strategic leadership, competitive advantage, and institutional change.",
    },
    {
        "name": "Corporate Governance",
        "icon": "bi-bank",
        "color": "#C62828",
        "description": "Corporate governance frameworks, regulatory systems, and public accountability.",
    },
    {
        "name": "Academic Writing & Publishing",
        "icon": "bi-journal-text",
        "color": "#4A148C",
        "description": "Dissertation writing, academic publishing, colloquium, and oral defence.",
    },
    {
        "name": "Teaching & Pedagogy",
        "icon": "bi-mortarboard-fill",
        "color": "#2E7D32",
        "description": "Higher education teaching techniques and student engagement.",
    },
]

# ── Course code → category name ───────────────────────────────────────────────

COURSE_CATEGORY = {
    # Year 1 Sem 1
    "BAD 705": "Business Administration",
    "DBAD 701": "Research Methods & Methodology",
    "DBAD 703": "Research Methods & Methodology",
    "DBAD 707A": "Finance & Accounting",
    "DBAD 707B": "Human Resource Management",
    "DBAD 707C": "Marketing Management",
    "DBAD 707D": "Strategic Management & Leadership",
    "DBAD 707E": "Corporate Governance",
    # Year 1 Sem 2
    "BDAD 702": "Research Methods & Methodology",
    "BDAD 704": "Business Administration",
    "BDAD 706": "Business Administration",
    "BDAD 708A": "Finance & Accounting",
    "BDAD 708B": "Human Resource Management",
    "BDAD 708C": "Marketing Management",
    "BDAD 708D": "Strategic Management & Leadership",
    "BDAD 708E": "Corporate Governance",
    # Year 2
    "BDAD 700A": "Research Methods & Methodology",
    "BDAD 709": "Research Methods & Methodology",
    "BDAD 711": "Research Methods & Methodology",
    "BDAD 713": "Research Methods & Methodology",
    "BDAD 700B": "Research Methods & Methodology",
    "BDAD 714": "Academic Writing & Publishing",
    "BDAD 716": "Academic Writing & Publishing",
    "BDAD 718": "Teaching & Pedagogy",
    # Year 3
    "BDAD 700C": "Research Methods & Methodology",
    "BDAD 700D": "Academic Writing & Publishing",
    "BDAD 700E": "Academic Writing & Publishing",
    "BDAD 700F": "Academic Writing & Publishing",
    "BDAD 700G": "Academic Writing & Publishing",
}


# ── Filename parsing helpers ──────────────────────────────────────────────────

def _clean(text):
    """Normalise whitespace and common punctuation."""
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def parse_filename(filename):
    """
    Return dict with keys: title, author, publication_year, publisher.
    Handles two common filename conventions:
      1. Author - Title (Year, Publisher) - libgen.li.pdf
      2. [Journal ...] Author{year}{id} libgen.li.pdf
      3. Title{Author}{year} libgen.li.pdf
    """
    stem = Path(filename).stem
    # Remove common suffixes
    stem = re.sub(r'\s*[-–]\s*libgen\.li$', '', stem, flags=re.IGNORECASE)
    stem = re.sub(r'\s*libgen\.li$', '', stem, flags=re.IGNORECASE)
    stem = re.sub(r'\s*libgen$', '', stem, flags=re.IGNORECASE)
    stem = re.sub(r'\s*Anna\'s\s*Arc?\w*$', '', stem, flags=re.IGNORECASE)

    title, author, year, publisher = '', '', 0, ''

    # Pattern A: Author - Title (Year, Publisher)
    # e.g. "Philip Kotler, Kevin Keller - Marketing Management (2021, Pearson)"
    m = re.match(
        r'^(.+?)\s+-\s+(.+?)\s+\((\d{4})[,.]?\s*(.+?)?\).*$',
        stem
    )
    if m:
        author_raw, title_raw, yr, pub = m.group(1), m.group(2), m.group(3), m.group(4) or ''
        # Heuristic: author segment is the part before the dash that looks like a name list
        # If author_raw contains a year it's wrong — flip
        title = _clean(title_raw)
        author = _clean(author_raw)
        year = int(yr)
        publisher = _clean(pub.rstrip('-–').strip())
        return {'title': title, 'author': author, 'publication_year': year, 'publisher': publisher}

    # Pattern B: {Author}(Year){id}  or  Title{Author}(Year)
    # e.g. "Corporate Governance Principles{Tricker, Bob}(2017){111968546}"
    m = re.match(r'^(.+?)\{([^}]+)\}\s*\((\d{4})\)', stem)
    if m:
        title = _clean(m.group(1))
        author = _clean(m.group(2))
        year = int(m.group(3))
        return {'title': title, 'author': author, 'publication_year': year, 'publisher': ''}

    # Pattern C: [Journal ...] Author(Year)[doi]{id}
    m = re.match(r'^\[.+?\]\s+(.+?)\{([^}]+)\}\s*\((\d{4})', stem)
    if m:
        title = _clean(m.group(1))
        author = _clean(m.group(2))
        year = int(m.group(3))
        return {'title': title, 'author': author, 'publication_year': year, 'publisher': ''}

    # Pattern D: bare filename with year somewhere
    yr_m = re.search(r'\((\d{4})\)', stem)
    year = int(yr_m.group(1)) if yr_m else 2020
    # Use full stem as title, no author parsed
    title = _clean(stem)
    return {'title': title, 'author': 'Unknown', 'publication_year': year, 'publisher': ''}


def normalise_title(title):
    """Lower-case, strip edition noise and punctuation for dedup comparison."""
    t = title.lower()
    # Remove common edition markers
    t = re.sub(r'\d+(st|nd|rd|th)\s+ed(ition)?', '', t, flags=re.IGNORECASE)
    t = re.sub(r'(fifth|fourth|third|second|first|sixth)\s+edition', '', t, flags=re.IGNORECASE)
    t = re.sub(r',?\s*\d+\s*e\b', '', t)
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'[^\w\s]', '', t)
    return t.strip()


def safe_filename(title, ext='.pdf'):
    """Generate a filesystem-safe filename from a title."""
    name = re.sub(r'[^\w\s-]', '', title)
    name = re.sub(r'[\s_]+', '-', name).strip('-')[:120]
    return name.lower() + ext


def parse_semester(year_folder):
    """
    'YEAR 1 SEMESTER 1' → ('Year 1, Semester 1', 'year-1-semester-1')
    """
    m = re.match(r'YEAR\s+(\d+)\s+SEMESTER\s+(\d+)', year_folder, re.IGNORECASE)
    if m:
        label = f"Year {m.group(1)}, Semester {m.group(2)}"
        tag = f"year-{m.group(1)}-semester-{m.group(2)}"
        return label, tag
    return year_folder, year_folder.lower().replace(' ', '-')


def parse_course(subdir_name):
    """
    'DBAD 701 Research Philosophy and Methodology' → ('DBAD 701', 'Research Philosophy and Methodology')
    """
    m = re.match(r'^([A-Z]+\s+\d+[A-Z]?)\s+(.+)$', subdir_name)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return subdir_name, subdir_name


# ── Main command ──────────────────────────────────────────────────────────────

class Command(BaseCommand):
    help = 'Seed database with real PhD textbooks from the Phd Books for E-library directory'

    def add_arguments(self, parser):
        parser.add_argument(
            '--books-dir',
            default=None,
            help='Path to "Phd Books for E-library" directory (auto-detected if omitted)',
        )
        parser.add_argument(
            '--no-copy',
            action='store_true',
            help='Do not copy PDF files to media/publications/ (use absolute paths)',
        )

    def handle(self, *args, **options):
        # ── Locate source directory ────────────────────────────────────────
        books_dir = options['books_dir']
        if not books_dir:
            # Auto-detect: sibling of the project directory
            base = Path(settings.BASE_DIR).parent
            candidates = [
                base / 'Phd Books for E-library',
                base / 'PhD Books for E Library',
                Path(settings.BASE_DIR) / 'Phd Books for E-library',
            ]
            for c in candidates:
                if c.exists():
                    books_dir = str(c)
                    break

        if not books_dir or not Path(books_dir).exists():
            self.stderr.write(self.style.ERROR(
                f'Books directory not found. Pass --books-dir "path/to/Phd Books for E-library"'
            ))
            return

        books_dir = Path(books_dir)
        self.stdout.write(f'[DIR] Books source: {books_dir}\n')

        # ── Prepare media directories ──────────────────────────────────────
        media_publications = Path(settings.MEDIA_ROOT) / 'publications'
        media_publications.mkdir(parents=True, exist_ok=True)

        # ── Wipe existing data ─────────────────────────────────────────────
        self.stdout.write('[DEL]  Clearing existing publications and categories...')
        Publication.objects.all().delete()
        Category.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('   Done.\n'))

        # ── Create categories ──────────────────────────────────────────────
        cat_map = {}
        for cat_data in CATEGORIES:
            cat = Category.objects.create(
                name=cat_data['name'],
                description=cat_data['description'],
                icon=cat_data['icon'],
                color=cat_data['color'],
            )
            cat_map[cat.name] = cat
            self.stdout.write(f'   [CAT] Category: {cat.name}')

        self.stdout.write('')

        # ── Get or create admin user ───────────────────────────────────────
        admin = User.objects.filter(is_superuser=True).first()
        if not admin:
            admin = User.objects.create_superuser(
                email='admin@ugc.edu.gh',
                username='admin',
                password='admin123',
                first_name='Admin',
                last_name='UGC',
            )
            self.stdout.write(self.style.SUCCESS('[OK] Superuser created: admin@ugc.edu.gh / admin123'))

        # ── Walk directory and collect PDF info ────────────────────────────
        # title_norm → Publication instance  (dedup map)
        title_map = {}
        created_count = 0
        tagged_count = 0

        # Walk: books_dir / YEAR X SEMESTER Y / COURSE CODE NAME / file.pdf
        year_folders = sorted([
            d for d in books_dir.iterdir()
            if d.is_dir() and re.match(r'YEAR\s+\d', d.name, re.IGNORECASE)
        ])

        for year_folder in year_folders:
            semester_label, semester_tag = parse_semester(year_folder.name)

            course_folders = sorted([d for d in year_folder.iterdir() if d.is_dir()])

            for course_folder in course_folders:
                course_code, course_name = parse_course(course_folder.name)
                category_name = COURSE_CATEGORY.get(course_code, 'Research Methods & Methodology')
                category = cat_map[category_name]
                course_tag = course_code.lower().replace(' ', '-')

                pdf_files = list(course_folder.glob('*.pdf'))

                for pdf_path in sorted(pdf_files):
                    meta = parse_filename(pdf_path.name)

                    # Skip empty titles
                    if not meta['title'] or len(meta['title']) < 3:
                        continue

                    norm = normalise_title(meta['title'])

                    if norm in title_map:
                        # Duplicate — just add new tags
                        pub = title_map[norm]
                        pub.tags.add(semester_tag, course_tag)
                        # Update semester field if it's not set or differs
                        if pub.semester and semester_label not in pub.semester:
                            pub.semester = pub.semester + '; ' + semester_label
                            pub.save(update_fields=['semester'])
                        tagged_count += 1
                        self.stdout.write(f'   [DUP]  Duplicate (tagged): {meta["title"][:60]}')
                        continue

                    # Copy PDF to media
                    dest_filename = safe_filename(meta['title'])
                    dest_path = media_publications / dest_filename
                    # Avoid filename collisions
                    counter = 1
                    while dest_path.exists():
                        dest_path = media_publications / safe_filename(
                            meta['title'] + f'-{counter}'
                        )
                        counter += 1

                    if not options['no_copy']:
                        try:
                            shutil.copy2(str(pdf_path), str(dest_path))
                        except Exception as e:
                            self.stderr.write(f'   [WARN]  Could not copy {pdf_path.name}: {e}')
                            dest_path = None

                    # Relative path for Django FileField
                    if dest_path and dest_path.exists():
                        file_field = f'publications/{dest_path.name}'
                    else:
                        file_field = None

                    # Determine publication type
                    pub_type = 'book'
                    title_lower = meta['title'].lower()
                    if any(k in title_lower for k in ['journal', 'annals', 'review', 'quarterly']):
                        pub_type = 'journal'
                    elif any(k in title_lower for k in ['principles', 'g20', 'oecd', 'global financial stability']):
                        pub_type = 'report'

                    pub = Publication(
                        title=meta['title'],
                        author=meta['author'],
                        abstract=f"A key text for {course_name} at the University of Gold Coast PhD in Business Administration programme.",
                        category=category,
                        publication_type=pub_type,
                        publication_year=meta['publication_year'] if meta['publication_year'] else 2020,
                        publisher=meta['publisher'],
                        institution='University of Gold Coast',
                        language='English',
                        keywords=f"{course_name}, {category_name}, PhD, Business Administration",
                        semester=semester_label,
                        is_open_access=True,
                        is_published=True,
                        status='published',
                        uploaded_by=admin,
                    )
                    if file_field:
                        pub.file.name = file_field
                    pub.save()

                    pub.tags.add(semester_tag, course_tag)

                    title_map[norm] = pub
                    created_count += 1
                    self.stdout.write(
                        f'   [OK] [{category_name[:20]}] {meta["title"][:55]}'
                        f' ({meta["publication_year"]})'
                    )

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'\n[DONE] Done!\n'
            f'   [BOOKS] {created_count} unique publications created\n'
            f'   [TAG]  {tagged_count} duplicate files tagged (not duplicated)\n'
            f'   [CAT] {len(CATEGORIES)} categories\n'
        ))
        self.stdout.write(f'   Run: python manage.py generate_thumbnails')
        self.stdout.write(f'   Then restart the dev server.\n')
