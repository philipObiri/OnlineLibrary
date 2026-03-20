"""
Library app - Admin Configuration
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Publication, Bookmark, DownloadHistory, RecentlyViewed


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'publication_count', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'publication_type', 'publication_year',
                    'is_open_access', 'is_published', 'view_count', 'download_count', 'created_at']
    list_filter = ['category', 'publication_type', 'is_open_access', 'is_published', 'publication_year']
    search_fields = ['title', 'author', 'abstract', 'keywords']
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ['view_count', 'download_count', 'created_at', 'updated_at']
    list_per_page = 25
    date_hierarchy = 'created_at'

    def cover_preview(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" height="60"/>', obj.cover_image.url)
        return '—'
    cover_preview.short_description = 'Cover'

    fieldsets = (
        ('Core Info', {'fields': ('title', 'slug', 'author', 'co_authors', 'abstract')}),
        ('Classification', {'fields': ('category', 'publication_type', 'publication_year', 'institution')}),
        ('Publication Details', {'fields': ('publisher', 'journal_name', 'volume', 'issue', 'pages', 'doi', 'isbn')}),
        ('Files & Access', {'fields': ('file', 'cover_image', 'external_url', 'is_open_access', 'is_published', 'status')}),
        ('Metadata', {'fields': ('language', 'keywords', 'uploaded_by')}),
        ('Stats', {'fields': ('view_count', 'download_count', 'created_at', 'updated_at'), 'classes': ['collapse']}),
    )


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ['user', 'publication', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'publication__title']


@admin.register(DownloadHistory)
class DownloadHistoryAdmin(admin.ModelAdmin):
    list_display = ['user', 'publication', 'timestamp', 'ip_address']
    list_filter = ['timestamp']
    search_fields = ['user__email', 'publication__title']
    readonly_fields = ['timestamp']
