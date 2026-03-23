"""
Management command: fetch_online_resources
Fetches free, open-access academic journal articles and preprints from public APIs
and imports them into the GoldVault library database.

Supported sources:
  - OpenAlex  (https://api.openalex.org)  — no API key required
  - DOAJ      (https://doaj.org/api)      — no API key required
  - arXiv     (https://arxiv.org/api)     — no API key required

Usage:
    python manage.py fetch_online_resources
    python manage.py fetch_online_resources --source openAlex
    python manage.py fetch_online_resources --source doaj --limit 50
    python manage.py fetch_online_resources --source arxiv --category "Research Methods & Methodology"
    python manage.py fetch_online_resources --dry-run --limit 5
"""

import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

import requests
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from library.models import Category, Publication

User = get_user_model()

# ---------------------------------------------------------------------------
# Category → search query mapping
# ---------------------------------------------------------------------------

SUBJECT_QUERIES = {
    "Research Methods": [
        "research methodology",
        "qualitative research",
        "mixed methods research",
    ],
    "Business Administration": [
        "business administration",
        "organisational theory",
        "management science",
    ],
    "Finance & Accounting": [
        "corporate finance",
        "financial accounting",
        "capital markets",
    ],
    "Human Resource Management": [
        "human resource management",
        "organizational behaviour",
        "talent management",
    ],
    "Marketing Management": [
        "marketing strategy",
        "consumer behaviour",
        "digital marketing",
    ],
    "Strategic Management & Leadership": [
        "strategic management",
        "competitive advantage",
        "corporate leadership",
    ],
    "Corporate Governance": [
        "corporate governance",
        "board of directors",
        "institutional governance",
    ],
    "Academic Writing & Publishing": [
        "academic writing",
        "scholarly publishing",
        "research communication",
    ],
}

OPENALEX_EMAIL = "library@ugc.edu.gh"  # polite pool — increases rate limit

# arXiv subject categories relevant to this library's disciplines
ARXIV_CATEGORIES = {
    "Research Methods":                  "stat.ME econ.EM",
    "Business Administration":           "econ.GN q-fin.GN",
    "Finance & Accounting":              "q-fin.GN q-fin.PM q-fin.RM",
    "Human Resource Management":         "econ.GN",
    "Marketing Management":              "econ.GN",
    "Strategic Management & Leadership": "econ.GN",
    "Corporate Governance":              "econ.GN q-fin.GN",
    "Academic Writing & Publishing":     "cs.DL",
}


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _norm_title(title: str) -> str:
    """Normalise a title for duplicate detection."""
    return re.sub(r"[^\w\s]", "", title.lower()).strip()


def _is_relevant(title: str, abstract: str, query: str) -> bool:
    """
    Return True only if at least one meaningful term from the query
    appears in the title or abstract. Prevents off-topic results.
    """
    haystack = (title + " " + abstract).lower()
    # Extract individual words from the query, ignore stop-words under 4 chars
    stop = {"and", "the", "for", "with", "from", "that", "this", "into"}
    terms = [w for w in re.findall(r"\b[a-z]{4,}\b", query.lower()) if w not in stop]
    if not terms:
        return True  # no meaningful terms to check against
    # At least 2 terms (or all if fewer than 2) must appear
    matches = sum(1 for t in terms if t in haystack)
    threshold = min(2, len(terms))
    return matches >= threshold


def _first_admin():
    """Return the first superuser to attach as uploaded_by."""
    return User.objects.filter(is_superuser=True).first()


def _get_or_create_category(name: str):
    """Return Category by name, or None if not found."""
    try:
        return Category.objects.get(name=name)
    except Category.DoesNotExist:
        return None


COVER_PALETTE = [
    (0x1B, 0x3A, 0x6B),  # Deep Navy
    (0x2D, 0x5F, 0x8A),  # Steel Blue
    (0xC9, 0xA8, 0x4C),  # Antique Gold
    (0x2E, 0x7D, 0x32),  # Forest Green
    (0x6A, 0x1B, 0x9A),  # Purple
    (0xC6, 0x28, 0x28),  # Crimson
    (0x00, 0x69, 0x5C),  # Teal
]


def _generate_cover(pub, covers_dir: Path) -> str | None:
    """
    Create a styled JPEG placeholder cover for an online article using Pillow.
    Returns the relative media path ('covers/<slug>.jpg') or None on failure.
    """
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return None

    covers_dir.mkdir(parents=True, exist_ok=True)
    safe_name = pub.slug[:180]  # keep well under Linux's 255-byte filename limit
    cover_path = covers_dir / f"{safe_name}.jpg"
    if cover_path.exists():
        return f"covers/{safe_name}.jpg"

    W, H = 300, 420
    bg = COVER_PALETTE[pub.pk % len(COVER_PALETTE)]
    img = Image.new("RGB", (W, H), bg)
    draw = ImageDraw.Draw(img)

    # Subtle inner border
    draw.rectangle([14, 14, W - 15, H - 15], outline=(255, 255, 255, 30), width=1)

    # Large faint initials
    words = pub.title.split()
    initials = (words[0][0] + (words[1][0] if len(words) > 1 else '')).upper()
    try:
        font_big = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 110)
        font_sm  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 13)
    except OSError:
        font_big = ImageFont.load_default()
        font_sm  = ImageFont.load_default()

    # Draw initials (faint white)
    bbox = draw.textbbox((0, 0), initials, font=font_big)
    tw = bbox[2] - bbox[0]
    draw.text(((W - tw) // 2, 140), initials, font=font_big,
              fill=(255, 255, 255, 40))

    # Publication type label
    label = pub.get_publication_type_display().upper()
    bbox2 = draw.textbbox((0, 0), label, font=font_sm)
    lw = bbox2[2] - bbox2[0]
    draw.text(((W - lw) // 2, 340), label, font=font_sm,
              fill=(255, 255, 255, 140))

    # Thin bottom accent stripe
    accent = tuple(min(255, c + 40) for c in bg)
    draw.rectangle([0, H - 6, W, H], fill=accent)

    img.save(str(cover_path), "JPEG", quality=80)
    return f"covers/{pub.slug}.jpg"


def _save_publication(data: dict, dry_run: bool, stdout) -> bool:
    """
    Persist one publication record.
    Returns True if saved (new), False if skipped (duplicate / dry-run).
    """
    title = (data.get("title") or "").strip()
    if not title:
        return False

    doi = (data.get("doi") or "").strip()

    # --- dedup by DOI ---
    if doi and Publication.objects.filter(doi=doi).exists():
        stdout.write(f"  [skip-doi] {title[:80]}")
        return False

    # --- dedup by normalised title ---
    norm = _norm_title(title)
    if Publication.objects.filter(title__iexact=title).exists():
        stdout.write(f"  [skip-title] {title[:80]}")
        return False

    if dry_run:
        stdout.write(f"  [dry-run] {title[:80]}")
        return False

    category = data.get("category_obj")
    admin = _first_admin()

    pub = Publication(
        title=title[:500],
        author=(data.get("author", "Unknown") or "Unknown")[:200],
        co_authors=(data.get("co_authors", "") or "")[:500],
        abstract=data.get("abstract", "No abstract available."),
        category=category,
        publication_type=data.get("publication_type", "journal"),
        publication_year=data.get("year", datetime.now().year),
        journal_name=(data.get("journal_name", "") or "")[:255],
        volume=(data.get("volume", "") or "")[:50],
        issue=(data.get("issue", "") or "")[:50],
        pages=(data.get("pages", "") or "")[:50],
        doi=doi[:255],
        external_url=(data.get("external_url", "") or "")[:200],
        is_open_access=True,
        is_published=True,
        status="published",
        institution="External / Open Access",
        language="English",
        keywords=data.get("keywords", ""),
        uploaded_by=admin,
    )
    pub.save()

    # Generate a Pillow placeholder cover image (online articles have no PDF)
    from django.conf import settings as django_settings
    covers_dir = Path(django_settings.MEDIA_ROOT) / 'covers'
    cover_rel = _generate_cover(pub, covers_dir)
    if cover_rel:
        pub.cover_image = cover_rel
        pub.save(update_fields=['cover_image'])

    # Tags: source identifier + category slug
    tags = [data.get("source_tag", "source:unknown")]
    if category:
        tags.append(category.slug)
    pub.tags.add(*tags)

    return True


# ---------------------------------------------------------------------------
# OpenAlex fetcher
# ---------------------------------------------------------------------------

def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """Rebuild plain-text abstract from OpenAlex inverted index."""
    if not inverted_index:
        return ""
    positions = []
    for word, pos_list in inverted_index.items():
        for pos in pos_list:
            positions.append((pos, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def fetch_openalex(query: str, limit: int, category_name: str = "") -> list[dict]:
    """Fetch open-access journal articles from OpenAlex."""
    url = "https://api.openalex.org/works"
    params = {
        # title_and_abstract.search is much tighter than the general 'search' param
        "filter": f"is_oa:true,type:journal-article,title_and_abstract.search:{query}",
        "per-page": min(limit, 50),
        "select": "title,authorships,abstract_inverted_index,doi,primary_location,publication_year,biblio",
        "mailto": OPENALEX_EMAIL,
        "sort": "relevance_score:desc",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    results = []
    for item in resp.json().get("results", []):
        authors = item.get("authorships", [])
        first_author = authors[0]["author"]["display_name"] if authors else "Unknown"
        co_authors = ", ".join(
            a["author"]["display_name"] for a in authors[1:6]
        )

        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}

        doi_raw = item.get("doi") or ""
        doi = doi_raw.replace("https://doi.org/", "").strip()

        abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
        biblio = item.get("biblio") or {}
        title = item.get("title", "")

        if not _is_relevant(title, abstract, query):
            continue

        results.append({
            "title": title,
            "author": first_author,
            "co_authors": co_authors,
            "abstract": abstract or "See full article via the link below.",
            "year": item.get("publication_year") or datetime.now().year,
            "doi": doi,
            "journal_name": source.get("display_name", ""),
            "volume": str(biblio.get("volume") or ""),
            "issue": str(biblio.get("issue") or ""),
            "pages": biblio.get("first_page", "") + (
                f"–{biblio['last_page']}" if biblio.get("last_page") else ""
            ),
            "external_url": loc.get("landing_page_url") or (
                f"https://doi.org/{doi}" if doi else ""
            ),
            "publication_type": "journal",
            "source_tag": "source:openalex",
        })
    return results


# ---------------------------------------------------------------------------
# DOAJ fetcher
# ---------------------------------------------------------------------------

def fetch_doaj(query: str, limit: int, category_name: str = "") -> list[dict]:
    """Fetch articles from the Directory of Open Access Journals."""
    # Target title and abstract fields only — prevents off-topic results
    field_query = f'bibjson.title:"{query}" OR bibjson.abstract:"{query}"'
    encoded = urllib.parse.quote(field_query)
    url = f"https://doaj.org/api/search/articles/{encoded}"
    params = {"pageSize": min(limit, 50)}
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    results = []
    for item in resp.json().get("results", []):
        bib = item.get("bibjson", {})

        authors_list = bib.get("author", [])
        first_author = authors_list[0].get("name", "Unknown") if authors_list else "Unknown"
        co_authors = ", ".join(a.get("name", "") for a in authors_list[1:6])

        # DOI
        doi = ""
        for ident in bib.get("identifier", []):
            if ident.get("type") == "doi":
                doi = ident.get("id", "")
                break

        # Full-text URL
        external_url = ""
        for link in bib.get("link", []):
            if link.get("type") == "fulltext":
                external_url = link.get("url", "")
                break
        if not external_url and doi:
            external_url = f"https://doi.org/{doi}"

        year_raw = bib.get("year")
        try:
            year = int(year_raw)
        except (TypeError, ValueError):
            year = datetime.now().year

        title = bib.get("title", "")
        abstract = bib.get("abstract", "")

        if not _is_relevant(title, abstract, query):
            continue

        results.append({
            "title": title,
            "author": first_author,
            "co_authors": co_authors,
            "abstract": abstract or "See full article via the link below.",
            "year": year,
            "doi": doi,
            "journal_name": bib.get("journal", {}).get("title", ""),
            "volume": str(bib.get("journal", {}).get("volume") or ""),
            "issue": str(bib.get("journal", {}).get("number") or ""),
            "pages": bib.get("start_page", "") + (
                f"–{bib['end_page']}" if bib.get("end_page") else ""
            ),
            "external_url": external_url,
            "publication_type": "journal",
            "source_tag": "source:doaj",
        })
    return results


# ---------------------------------------------------------------------------
# arXiv fetcher
# ---------------------------------------------------------------------------

ARXIV_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}


def fetch_arxiv(query: str, limit: int, category_name: str = "") -> list[dict]:
    """Fetch preprints from arXiv."""
    # Search title AND abstract only (not full text) for tighter relevance
    encoded_q = urllib.parse.quote(query)
    search = f"ti:{encoded_q}+AND+abs:{encoded_q}"

    # Restrict to relevant subject categories for this library
    cats = ARXIV_CATEGORIES.get(category_name, "econ.GN q-fin.GN stat.ME")
    cat_filter = "+OR+".join(f"cat:{c}" for c in cats.split())
    if cat_filter:
        search = f"({search})+AND+({cat_filter})"

    url = (
        f"http://export.arxiv.org/api/query"
        f"?search_query={search}&max_results={min(limit, 50)}&sortBy=relevance"
    )
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except requests.RequestException:
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        return []

    results = []
    for entry in root.findall("atom:entry", ARXIV_NS):
        title_el = entry.find("atom:title", ARXIV_NS)
        title = (title_el.text or "").strip().replace("\n", " ") if title_el is not None else ""

        summary_el = entry.find("atom:summary", ARXIV_NS)
        abstract = (summary_el.text or "").strip() if summary_el is not None else ""

        id_el = entry.find("atom:id", ARXIV_NS)
        arxiv_id_url = (id_el.text or "").strip() if id_el is not None else ""

        doi_el = entry.find("arxiv:doi", ARXIV_NS)
        doi = (doi_el.text or "").strip() if doi_el is not None else ""

        published_el = entry.find("atom:published", ARXIV_NS)
        year = datetime.now().year
        if published_el is not None and published_el.text:
            try:
                year = int(published_el.text[:4])
            except ValueError:
                pass

        author_els = entry.findall("atom:author", ARXIV_NS)
        authors = []
        for a in author_els:
            name_el = a.find("atom:name", ARXIV_NS)
            if name_el is not None and name_el.text:
                authors.append(name_el.text.strip())

        first_author = authors[0] if authors else "Unknown"
        co_authors = ", ".join(authors[1:6])

        if not _is_relevant(title, abstract, query):
            continue

        results.append({
            "title": title,
            "author": first_author,
            "co_authors": co_authors,
            "abstract": abstract or "See full article via the link below.",
            "year": year,
            "doi": doi,
            "journal_name": "arXiv Preprint",
            "volume": "",
            "issue": "",
            "pages": "",
            "external_url": arxiv_id_url,
            "publication_type": "preprint",
            "source_tag": "source:arxiv",
        })
    return results


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Fetch free open-access journal articles and preprints from "
        "OpenAlex, DOAJ, and arXiv and import them into GoldVault."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            choices=["openAlex", "doaj", "arxiv", "all"],
            default="all",
            help="Which source(s) to fetch from (default: all).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=30,
            help="Max results per source per category query (default: 30).",
        )
        parser.add_argument(
            "--category",
            default=None,
            help="Restrict fetching to a single category name.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would be imported without saving anything.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        limit = options["limit"]
        target_category = options["category"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN — nothing will be saved ---"))

        # Build list of (category_name, [queries]) pairs to process
        if target_category:
            if target_category not in SUBJECT_QUERIES:
                self.stderr.write(
                    self.style.ERROR(
                        f"Unknown category '{target_category}'. "
                        f"Valid options: {list(SUBJECT_QUERIES.keys())}"
                    )
                )
                return
            categories = {target_category: SUBJECT_QUERIES[target_category]}
        else:
            categories = SUBJECT_QUERIES

        # Determine which fetchers to run
        fetchers = []
        if source in ("openAlex", "all"):
            fetchers.append(("OpenAlex", fetch_openalex))
        if source in ("doaj", "all"):
            fetchers.append(("DOAJ", fetch_doaj))
        if source in ("arxiv", "all"):
            fetchers.append(("arXiv", fetch_arxiv))

        total_saved = 0
        total_skipped = 0

        for cat_name, queries in categories.items():
            cat_obj = _get_or_create_category(cat_name)
            if cat_obj is None:
                self.stdout.write(
                    self.style.WARNING(f"\nCategory not found in DB: '{cat_name}' — skipping.")
                )
                continue

            self.stdout.write(self.style.HTTP_INFO(f"\n=== {cat_name} ==="))

            for source_name, fetcher in fetchers:
                self.stdout.write(f"\n  [{source_name}]")
                for query in queries:
                    self.stdout.write(f"    Query: \"{query}\"")
                    articles = fetcher(query, limit, category_name=cat_name)
                    if not articles:
                        self.stdout.write("      No results or API error.")
                        continue

                    for article in articles:
                        article["category_obj"] = cat_obj
                        saved = _save_publication(article, dry_run, self.stdout)
                        if saved:
                            total_saved += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f"      [saved] {article['title'][:80]}"
                                )
                            )
                        else:
                            total_skipped += 1

                    # Be polite to free APIs
                    time.sleep(0.5)

        self.stdout.write("")
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"Dry run complete. Would have saved {total_saved} articles "
                    f"(skipped {total_skipped} duplicates)."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Saved {total_saved} new articles, "
                    f"skipped {total_skipped} duplicates."
                )
            )
