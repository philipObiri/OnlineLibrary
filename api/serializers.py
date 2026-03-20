"""
API app - DRF Serializers
"""
from rest_framework import serializers
from taggit.serializers import TagListSerializerField, TaggitSerializer
from library.models import Publication, Category, Bookmark, DownloadHistory
from users.models import User


class CategorySerializer(serializers.ModelSerializer):
    publication_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'icon', 'color', 'publication_count']

    def get_publication_count(self, obj):
        return obj.publications.filter(is_published=True).count()


class PublicationListSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    tags = TagListSerializerField()
    cover_url = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            'id', 'title', 'slug', 'author', 'co_authors', 'abstract',
            'category_name', 'category_slug', 'publication_type', 'publication_year',
            'publisher', 'is_open_access', 'view_count', 'download_count',
            'tags', 'cover_url', 'is_bookmarked', 'created_at',
        ]

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return obj.cover_url

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, publication=obj).exists()
        return False


class PublicationDetailSerializer(TaggitSerializer, serializers.ModelSerializer):
    """Full serializer for detail views."""
    category = CategorySerializer(read_only=True)
    tags = TagListSerializerField()
    cover_url = serializers.SerializerMethodField()
    citation_apa = serializers.CharField(read_only=True)
    citation_mla = serializers.CharField(read_only=True)
    is_bookmarked = serializers.SerializerMethodField()
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = Publication
        fields = [
            'id', 'title', 'slug', 'author', 'co_authors', 'abstract',
            'category', 'publication_type', 'publication_year', 'publisher',
            'journal_name', 'volume', 'issue', 'pages', 'doi', 'isbn',
            'is_open_access', 'is_published', 'institution', 'language', 'keywords',
            'view_count', 'download_count', 'tags', 'cover_url',
            'citation_apa', 'citation_mla', 'is_bookmarked', 'has_file',
            'external_url', 'created_at', 'updated_at',
        ]

    def get_cover_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return obj.cover_url

    def get_is_bookmarked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(user=request.user, publication=obj).exists()
        return False

    def get_has_file(self, obj):
        return bool(obj.file) or bool(obj.external_url)


class BookmarkSerializer(serializers.ModelSerializer):
    publication = PublicationListSerializer(read_only=True)

    class Meta:
        model = Bookmark
        fields = ['id', 'publication', 'created_at', 'notes']


class DownloadHistorySerializer(serializers.ModelSerializer):
    publication = PublicationListSerializer(read_only=True)

    class Meta:
        model = DownloadHistory
        fields = ['id', 'publication', 'timestamp']


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'username', 'first_name', 'last_name', 'role',
                  'institution', 'department', 'research_area', 'bio', 'avatar_url']
        read_only_fields = ['email', 'avatar_url']
