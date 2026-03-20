"""
API app - Django REST Framework Views
"""
from rest_framework import generics, viewsets, status, filters
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from library.models import Publication, Category, Bookmark, DownloadHistory, RecentlyViewed
from users.models import User
from .serializers import (
    PublicationListSerializer, PublicationDetailSerializer,
    CategorySerializer, BookmarkSerializer, DownloadHistorySerializer,
    UserProfileSerializer,
)
from .filters import PublicationFilter


class PublicationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for listing and retrieving publications.
    Supports AJAX live search and multi-filter.
    """
    queryset = Publication.objects.filter(is_published=True).select_related('category').prefetch_related('tags')
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PublicationFilter
    search_fields = ['title', 'author', 'abstract', 'keywords', 'tags__name', 'co_authors', 'institution']
    ordering_fields = ['publication_year', 'title', 'view_count', 'download_count', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PublicationDetailSerializer
        return PublicationListSerializer

    def get_serializer_context(self):
        return {'request': self.request}

    @method_decorator(cache_page(60 * 5))
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        AJAX live search endpoint.
        GET /api/publications/search/?q=keyword&category=slug&year_from=2020
        """
        q = request.query_params.get('q', '').strip()
        queryset = self.get_queryset()

        if q:
            queryset = queryset.filter(
                Q(title__icontains=q) |
                Q(author__icontains=q) |
                Q(abstract__icontains=q) |
                Q(keywords__icontains=q) |
                Q(tags__name__icontains=q)
            ).distinct()

        # Apply filters
        category = request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)

        pub_type = request.query_params.get('type')
        if pub_type:
            queryset = queryset.filter(publication_type=pub_type)

        year_from = request.query_params.get('year_from')
        year_to = request.query_params.get('year_to')
        if year_from:
            queryset = queryset.filter(publication_year__gte=int(year_from))
        if year_to:
            queryset = queryset.filter(publication_year__lte=int(year_to))

        open_access = request.query_params.get('open_access')
        if open_access == '1':
            queryset = queryset.filter(is_open_access=True)

        author = request.query_params.get('author', '').strip()
        if author:
            queryset = queryset.filter(author__icontains=author)

        sort = request.query_params.get('sort', '-created_at')
        valid_sorts = ['-created_at', 'created_at', '-publication_year', 'publication_year',
                       'title', '-view_count', '-download_count']
        if sort in valid_sorts:
            queryset = queryset.order_by(sort)

        # Paginate
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = PublicationListSerializer(page, many=True, context={'request': request})
            response = self.get_paginated_response(serializer.data)
            response.data['total_count'] = queryset.count()
            return response

        serializer = PublicationListSerializer(queryset, many=True, context={'request': request})
        return Response({'results': serializer.data, 'count': queryset.count()})

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Top publications by views."""
        featured = self.get_queryset().order_by('-view_count')[:6]
        serializer = PublicationListSerializer(featured, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Most recently added publications."""
        recent = self.get_queryset().order_by('-created_at')[:8]
        serializer = PublicationListSerializer(recent, many=True, context={'request': request})
        return Response(serializer.data)


class CategoryListView(generics.ListAPIView):
    """List all categories with publication counts."""
    queryset = Category.objects.annotate(
        pub_count=Count('publications', filter=Q(publications__is_published=True))
    ).order_by('-pub_count')
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    @method_decorator(cache_page(60 * 15))
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class BookmarkListView(generics.ListAPIView):
    """List authenticated user's bookmarks."""
    serializer_class = BookmarkSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user).select_related(
            'publication', 'publication__category'
        ).prefetch_related('publication__tags')


class BookmarkToggleView(APIView):
    """Toggle bookmark for a publication."""
    permission_classes = [IsAuthenticated]

    def post(self, request, slug):
        try:
            publication = Publication.objects.get(slug=slug, is_published=True)
        except Publication.DoesNotExist:
            return Response({'error': 'Publication not found.'}, status=status.HTTP_404_NOT_FOUND)

        bookmark, created = Bookmark.objects.get_or_create(
            user=request.user, publication=publication
        )
        if not created:
            bookmark.delete()
            return Response({
                'bookmarked': False,
                'message': 'Removed from bookmarks.',
                'count': publication.bookmarks.count()
            })

        return Response({
            'bookmarked': True,
            'message': 'Saved to bookmarks.',
            'count': publication.bookmarks.count()
        }, status=status.HTTP_201_CREATED)


class DownloadHistoryView(generics.ListAPIView):
    """List authenticated user's download history."""
    serializer_class = DownloadHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DownloadHistory.objects.filter(user=self.request.user).select_related(
            'publication', 'publication__category'
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Get and update the authenticated user's profile."""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class DashboardStatsView(APIView):
    """Aggregated stats for user dashboard."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        stats = {
            'bookmarks': Bookmark.objects.filter(user=user).count(),
            'downloads': DownloadHistory.objects.filter(user=user).count(),
            'recently_viewed': RecentlyViewed.objects.filter(user=user).count(),
        }
        return Response(stats)


@api_view(['GET'])
def autocomplete(request):
    """Fast autocomplete for search bar."""
    q = request.query_params.get('q', '').strip()
    if len(q) < 2:
        return Response({'results': []})

    publications = Publication.objects.filter(
        Q(title__icontains=q) | Q(author__icontains=q),
        is_published=True
    ).values('id', 'title', 'author', 'slug', 'publication_type')[:8]

    return Response({'results': list(publications)})


@api_view(['GET'])
def library_stats(request):
    """Public library statistics."""
    data = {
        'total_publications': Publication.objects.filter(is_published=True).count(),
        'open_access': Publication.objects.filter(is_open_access=True, is_published=True).count(),
        'total_categories': Category.objects.count(),
        'total_downloads': DownloadHistory.objects.count(),
    }
    return Response(data)
