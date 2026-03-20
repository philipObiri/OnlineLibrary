"""
API app - URL Patterns
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register(r'publications', views.PublicationViewSet, basename='publication')

urlpatterns = [
    # Router-generated URLs
    path('', include(router.urls)),

    # Categories
    path('categories/', views.CategoryListView.as_view(), name='api_categories'),

    # Bookmarks
    path('bookmarks/', views.BookmarkListView.as_view(), name='api_bookmarks'),
    path('bookmarks/toggle/<slug:slug>/', views.BookmarkToggleView.as_view(), name='api_bookmark_toggle'),

    # Downloads
    path('downloads/', views.DownloadHistoryView.as_view(), name='api_downloads'),

    # User
    path('user/profile/', views.UserProfileView.as_view(), name='api_profile'),
    path('user/stats/', views.DashboardStatsView.as_view(), name='api_stats'),

    # Utilities
    path('autocomplete/', views.autocomplete, name='api_autocomplete'),
    path('stats/', views.library_stats, name='api_library_stats'),

    # JWT Auth
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
