"""
Library app - Views (Class-Based + Function-Based)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, TemplateView
from django.http import FileResponse, Http404, JsonResponse
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.paginator import Paginator
import os

from .models import Publication, Category, Bookmark, DownloadHistory, RecentlyViewed
from .forms import PublicationForm, CategoryForm, UserAdminForm
from users.models import User


# ─── Landing Page ─────────────────────────────────────────────────────────────

@method_decorator(cache_page(60 * 10), name='dispatch')  # cache 10 min
class LandingView(TemplateView):
    template_name = 'library/landing.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        published = Publication.objects.filter(is_published=True)
        context['featured'] = published.select_related('category').order_by('-view_count', '-created_at')[:6]
        context['categories'] = Category.objects.annotate(
            pub_count=Count('publications', filter=Q(publications__is_published=True))
        ).order_by('-pub_count')[:8]
        context['total_publications'] = published.count()
        context['total_categories'] = Category.objects.count()
        context['open_access_count'] = published.filter(is_open_access=True).count()
        context['recent_publications'] = published.select_related('category').order_by('-created_at')[:4]
        return context


# ─── Catalogue ────────────────────────────────────────────────────────────────

class CatalogueView(ListView):
    model = Publication
    template_name = 'library/catalogue.html'
    context_object_name = 'publications'
    paginate_by = 12

    def get_queryset(self):
        qs = (
            Publication.objects
            .filter(is_published=True)
            .select_related('category')
            .prefetch_related('tags')
            .only(
                'id', 'title', 'slug', 'author', 'cover_image', 'publication_year',
                'publication_type', 'is_open_access', 'view_count', 'download_count',
                'category__name', 'category__slug',
            )
        )

        # Text search — title and author first (indexed), abstract as fallback
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(author__icontains=q) |
                Q(keywords__icontains=q) |
                Q(tags__name__icontains=q) |
                Q(abstract__icontains=q)
            ).distinct()

        # Filters
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category__slug=category)

        pub_type = self.request.GET.get('type')
        if pub_type:
            qs = qs.filter(publication_type=pub_type)

        year_from = self.request.GET.get('year_from')
        year_to = self.request.GET.get('year_to')
        if year_from:
            qs = qs.filter(publication_year__gte=int(year_from))
        if year_to:
            qs = qs.filter(publication_year__lte=int(year_to))

        open_access = self.request.GET.get('open_access')
        if open_access == '1':
            qs = qs.filter(is_open_access=True)

        author = self.request.GET.get('author', '').strip()
        if author:
            qs = qs.filter(author__icontains=author)

        sort = self.request.GET.get('sort', '-created_at')
        valid_sorts = ['-created_at', 'created_at', '-publication_year', 'publication_year',
                       'title', '-title', '-view_count', '-download_count']
        if sort in valid_sorts:
            qs = qs.order_by(sort)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.annotate(
            pub_count=Count('publications', filter=Q(publications__is_published=True))
        )
        context['publication_types'] = Publication.TYPE_CHOICES
        context['current_filters'] = {
            'q': self.request.GET.get('q', ''),
            'category': self.request.GET.get('category', ''),
            'type': self.request.GET.get('type', ''),
            'year_from': self.request.GET.get('year_from', ''),
            'year_to': self.request.GET.get('year_to', ''),
            'open_access': self.request.GET.get('open_access', ''),
            'author': self.request.GET.get('author', ''),
            'sort': self.request.GET.get('sort', '-created_at'),
        }
        context['total_results'] = self.get_queryset().count()
        # Year range for filter
        years = Publication.objects.filter(is_published=True).values_list('publication_year', flat=True).distinct()
        context['year_range'] = sorted(set(years), reverse=True)
        return context


# ─── Publication Detail ───────────────────────────────────────────────────────

class PublicationDetailView(DetailView):
    model = Publication
    template_name = 'library/publication_detail.html'
    context_object_name = 'publication'

    def get_object(self):
        obj = get_object_or_404(Publication, slug=self.kwargs['slug'], is_published=True)
        # Increment view count
        Publication.objects.filter(pk=obj.pk).update(view_count=obj.view_count + 1)
        # Track recently viewed
        if self.request.user.is_authenticated:
            RecentlyViewed.objects.update_or_create(
                user=self.request.user, publication=obj
            )
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pub = self.object
        
        # Related publications
        context['related'] = Publication.objects.filter(
            Q(category=pub.category) | Q(author=pub.author),
            is_published=True
        ).exclude(pk=pub.pk).select_related('category')[:4]
        
        # User bookmark status
        if self.request.user.is_authenticated:
            context['is_bookmarked'] = Bookmark.objects.filter(
                user=self.request.user, publication=pub
            ).exists()
        
        context['tags'] = pub.tags.all()
        return context


# ─── Download ─────────────────────────────────────────────────────────────────

@login_required
def download_publication(request, slug):
    """Secure file download with access control."""
    publication = get_object_or_404(Publication, slug=slug, is_published=True)

    # Access control
    if not publication.is_open_access and not request.user.is_staff:
        messages.error(request, 'This publication requires special access permissions.')
        return redirect('publication_detail', slug=slug)

    if not publication.file:
        if publication.external_url:
            return redirect(publication.external_url)
        messages.error(request, 'File not available for download.')
        return redirect('publication_detail', slug=slug)

    # Record download
    DownloadHistory.objects.create(
        user=request.user,
        publication=publication,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    Publication.objects.filter(pk=publication.pk).update(
        download_count=publication.download_count + 1
    )

    # Serve file
    try:
        response = FileResponse(
            publication.file.open('rb'),
            content_type='application/pdf',
            as_attachment=True,
            filename=f"{publication.slug}.pdf"
        )
        return response
    except Exception:
        raise Http404("File could not be served.")


# ─── Bookmark Toggle ──────────────────────────────────────────────────────────

@login_required
def toggle_bookmark(request, slug):
    """Toggle bookmark for a publication."""
    publication = get_object_or_404(Publication, slug=slug)
    bookmark, created = Bookmark.objects.get_or_create(
        user=request.user, publication=publication
    )
    if not created:
        bookmark.delete()
        bookmarked = False
    else:
        bookmarked = True

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'bookmarked': bookmarked, 'count': publication.bookmarks.count()})

    action = 'saved to' if bookmarked else 'removed from'
    messages.success(request, f'"{publication.title}" {action} your bookmarks.')
    return redirect(request.META.get('HTTP_REFERER', 'catalogue'))


# ─── Dashboard ────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """User dashboard with stats, bookmarks, history."""
    user = request.user
    bookmarks = Bookmark.objects.filter(user=user).select_related('publication', 'publication__category')[:10]
    downloads = DownloadHistory.objects.filter(user=user).select_related('publication', 'publication__category')[:10]
    recently_viewed = RecentlyViewed.objects.filter(user=user).select_related('publication', 'publication__category')[:6]
    
    # Recommendations: based on most viewed categories
    viewed_categories = RecentlyViewed.objects.filter(user=user).values_list(
        'publication__category', flat=True
    ).distinct()
    recommended = Publication.objects.filter(
        category__in=viewed_categories, is_published=True
    ).exclude(
        recently_viewed__user=user
    ).select_related('category').order_by('-view_count')[:6]

    context = {
        'bookmarks': bookmarks,
        'downloads': downloads,
        'recently_viewed': recently_viewed,
        'recommended': recommended,
        'bookmark_count': Bookmark.objects.filter(user=user).count(),
        'download_count': DownloadHistory.objects.filter(user=user).count(),
    }
    return render(request, 'library/dashboard.html', context)


# ─── Admin Panel ──────────────────────────────────────────────────────────────

class AdminRequiredMixin(UserPassesTestMixin):
    raise_exception = False
    login_url = '/auth/login/'

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    template_name = 'admin_panel/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_publications'] = Publication.objects.count()
        context['total_users'] = __import__('users.models', fromlist=['User']).User.objects.count()
        context['total_downloads'] = DownloadHistory.objects.count()
        context['total_bookmarks'] = Bookmark.objects.count()
        context['recent_publications'] = Publication.objects.select_related('category', 'uploaded_by').order_by('-created_at')[:10]
        context['popular_publications'] = Publication.objects.filter(is_published=True).order_by('-download_count')[:5]
        return context


class PublicationCreateView(AdminRequiredMixin, CreateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'admin_panel/publication_form.html'
    success_url = reverse_lazy('admin_dashboard')

    def form_valid(self, form):
        form.instance.uploaded_by = self.request.user
        messages.success(self.request, 'Publication created successfully!')
        return super().form_valid(form)


class PublicationUpdateView(AdminRequiredMixin, UpdateView):
    model = Publication
    form_class = PublicationForm
    template_name = 'admin_panel/publication_form.html'
    success_url = reverse_lazy('admin_dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Publication updated successfully!')
        return super().form_valid(form)


class PublicationDeleteView(AdminRequiredMixin, DeleteView):
    model = Publication
    template_name = 'admin_panel/publication_confirm_delete.html'
    success_url = reverse_lazy('admin_dashboard')

    def form_valid(self, form):
        messages.success(self.request, 'Publication deleted.')
        return super().form_valid(form)


# ─── Category Management ──────────────────────────────────────────────────────

class CategoryListView(AdminRequiredMixin, ListView):
    model = Category
    template_name = 'admin_panel/category_list.html'
    context_object_name = 'categories'

    def get_queryset(self):
        return Category.objects.annotate(
            pub_count=Count('publications')
        ).order_by('name')


class CategoryCreateView(AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_panel/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category created successfully!')
        return super().form_valid(form)


class CategoryUpdateView(AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'admin_panel/category_form.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category updated successfully!')
        return super().form_valid(form)


class CategoryDeleteView(AdminRequiredMixin, DeleteView):
    model = Category
    template_name = 'admin_panel/category_confirm_delete.html'
    success_url = reverse_lazy('category_list')

    def form_valid(self, form):
        messages.success(self.request, 'Category deleted.')
        return super().form_valid(form)


# ─── User Management ──────────────────────────────────────────────────────────

class UserListView(AdminRequiredMixin, ListView):
    model = User
    template_name = 'admin_panel/user_list.html'
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.order_by('-date_joined')
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(
                Q(email__icontains=q) | Q(first_name__icontains=q) |
                Q(last_name__icontains=q) | Q(username__icontains=q)
            )
        role = self.request.GET.get('role', '')
        if role:
            qs = qs.filter(role=role)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['role_choices'] = User.ROLE_CHOICES
        context['q'] = self.request.GET.get('q', '')
        context['current_role'] = self.request.GET.get('role', '')
        return context


class UserUpdateView(AdminRequiredMixin, UpdateView):
    model = User
    form_class = UserAdminForm
    template_name = 'admin_panel/user_form.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        messages.success(self.request, 'User updated successfully!')
        return super().form_valid(form)


class UserDeleteView(AdminRequiredMixin, DeleteView):
    model = User
    template_name = 'admin_panel/user_confirm_delete.html'
    success_url = reverse_lazy('user_list')

    def form_valid(self, form):
        if self.get_object() == self.request.user:
            messages.error(self.request, 'You cannot delete your own account.')
            return redirect('user_list')
        messages.success(self.request, 'User deleted.')
        return super().form_valid(form)
