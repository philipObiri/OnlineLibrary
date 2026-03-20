"""
Library app - URL Patterns
"""
from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.LandingView.as_view(), name='landing'),
    path('catalogue/', views.CatalogueView.as_view(), name='catalogue'),
    path('publication/<slug:slug>/', views.PublicationDetailView.as_view(), name='publication_detail'),

    # User actions
    path('download/<slug:slug>/', views.download_publication, name='download_publication'),
    path('bookmark/<slug:slug>/', views.toggle_bookmark, name='toggle_bookmark'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Admin panel
    path('manage/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('manage/publications/add/', views.PublicationCreateView.as_view(), name='publication_add'),
    path('manage/publications/<slug:slug>/edit/', views.PublicationUpdateView.as_view(), name='publication_edit'),
    path('manage/publications/<slug:slug>/delete/', views.PublicationDeleteView.as_view(), name='publication_delete'),

    # Category management
    path('manage/categories/', views.CategoryListView.as_view(), name='category_list'),
    path('manage/categories/add/', views.CategoryCreateView.as_view(), name='category_add'),
    path('manage/categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('manage/categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # User management
    path('manage/users/', views.UserListView.as_view(), name='user_list'),
    path('manage/users/<int:pk>/edit/', views.UserUpdateView.as_view(), name='user_edit'),
    path('manage/users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
]
