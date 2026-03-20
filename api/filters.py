"""
API app - Django Filters for Publications
"""
import django_filters
from library.models import Publication, Category


class PublicationFilter(django_filters.FilterSet):
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='exact')
    year_from = django_filters.NumberFilter(field_name='publication_year', lookup_expr='gte')
    year_to = django_filters.NumberFilter(field_name='publication_year', lookup_expr='lte')
    author = django_filters.CharFilter(field_name='author', lookup_expr='icontains')
    publication_type = django_filters.ChoiceFilter(choices=Publication.TYPE_CHOICES)
    is_open_access = django_filters.BooleanFilter()
    institution = django_filters.CharFilter(field_name='institution', lookup_expr='icontains')

    class Meta:
        model = Publication
        fields = ['category', 'year_from', 'year_to', 'author', 'publication_type', 'is_open_access', 'institution']
