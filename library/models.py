"""
Library app - Core Models for PhD Digital Library
"""
from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from taggit.managers import TaggableManager
from users.models import User


class Category(models.Model):
    """Publication categories / disciplines."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='Bootstrap icon class e.g. bi-book')
    color = models.CharField(max_length=7, default='#1B3A6B', help_text='Hex color')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def publication_count(self):
        return self.publications.filter(is_published=True).count()


class Publication(models.Model):
    """Core publication model for books, journals, theses, etc."""

    TYPE_CHOICES = [
        ('book', 'Book'),
        ('journal', 'Journal Article'),
        ('thesis', 'PhD Thesis'),
        ('dissertation', 'Dissertation'),
        ('conference', 'Conference Paper'),
        ('report', 'Research Report'),
        ('preprint', 'Preprint'),
    ]

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('archived', 'Archived'),
    ]

    # Core Fields
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=520, unique=True, blank=True)
    author = models.CharField(max_length=300)
    co_authors = models.CharField(max_length=500, blank=True)
    abstract = models.TextField()
    
    # Classification
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='publications')
    publication_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='book')
    publication_year = models.PositiveIntegerField()
    publisher = models.CharField(max_length=255, blank=True)
    journal_name = models.CharField(max_length=255, blank=True)
    volume = models.CharField(max_length=50, blank=True)
    issue = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)
    doi = models.CharField(max_length=255, blank=True, verbose_name='DOI')
    isbn = models.CharField(max_length=20, blank=True, verbose_name='ISBN')
    
    # Files & Media
    file = models.FileField(upload_to='publications/', null=True, blank=True)
    cover_image = models.ImageField(upload_to='covers/', null=True, blank=True)
    external_url = models.URLField(blank=True)
    
    # Access Control
    is_open_access = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='published')
    
    # Metadata
    tags = TaggableManager(blank=True)
    institution = models.CharField(max_length=255, blank=True)
    language = models.CharField(max_length=50, default='English')
    keywords = models.TextField(blank=True, help_text='Comma-separated keywords')
    semester = models.CharField(max_length=50, blank=True, help_text='e.g. Year 1, Semester 1')
    
    # Stats
    view_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_publications')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'publications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['publication_year']),
            models.Index(fields=['author']),
            models.Index(fields=['category']),
            models.Index(fields=['publication_type']),
            models.Index(fields=['is_open_access', 'is_published']),
            models.Index(fields=['is_published', '-created_at']),
            models.Index(fields=['is_published', '-view_count']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return f"{self.title} ({self.publication_year})"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Publication.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('publication_detail', kwargs={'slug': self.slug})

    @property
    def cover_url(self):
        if self.cover_image:
            return self.cover_image.url
        # Generate a deterministic placeholder based on category
        colors = ['1B3A6B', '2D5F8A', 'C9A84C', '2E7D32', '6A1B9A', 'C62828', '00695C']
        color = colors[self.pk % len(colors)] if self.pk else '1B3A6B'
        title_short = self.title[:20].replace(' ', '+')
        return f"https://via.placeholder.com/300x420/{color}/FFFFFF?text={title_short}"

    @property
    def citation_apa(self):
        """Generate APA citation."""
        authors = self.author
        if self.co_authors:
            authors += f", {self.co_authors}"
        year = self.publication_year
        title = self.title
        if self.publication_type == 'journal':
            return f"{authors} ({year}). {title}. *{self.journal_name}*, {self.volume}({self.issue}), {self.pages}."
        elif self.publication_type in ['thesis', 'dissertation']:
            return f"{authors} ({year}). *{title}* [Doctoral dissertation, {self.institution}]."
        else:
            pub = self.publisher or self.institution
            return f"{authors} ({year}). *{title}*. {pub}."

    @property
    def citation_mla(self):
        """Generate MLA citation."""
        authors = self.author
        title = self.title
        year = self.publication_year
        if self.publication_type == 'journal':
            return f'{authors}. "{title}." *{self.journal_name}*, vol. {self.volume}, no. {self.issue}, {year}, pp. {self.pages}.'
        else:
            pub = self.publisher or self.institution
            return f'{authors}. *{title}*. {pub}, {year}.'


class Bookmark(models.Model):
    """User bookmarks / saved publications."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = 'bookmarks'
        unique_together = ['user', 'publication']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} → {self.publication.title}"


class DownloadHistory(models.Model):
    """Track user downloads."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_history')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='download_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        db_table = 'download_history'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.email} downloaded {self.publication.title}"


class RecentlyViewed(models.Model):
    """Track recently viewed publications per user."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recently_viewed')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='recently_viewed')
    viewed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recently_viewed'
        unique_together = ['user', 'publication']
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.email} viewed {self.publication.title}"
