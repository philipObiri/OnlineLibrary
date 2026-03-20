"""
Library app - Forms
"""
from django import forms
from .models import Publication, Category
from users.models import User


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'icon', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'sv-form-input', 'placeholder': 'e.g. Computer Science'}),
            'description': forms.Textarea(attrs={'class': 'sv-form-input', 'rows': 3}),
            'icon': forms.TextInput(attrs={'class': 'sv-form-input', 'placeholder': 'bi-book'}),
            'color': forms.TextInput(attrs={'class': 'sv-form-input', 'type': 'color'}),
        }


class UserAdminForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'username', 'role', 'institution',
                  'department', 'research_area', 'is_verified', 'is_staff', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'sv-form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'sv-form-input'}),
            'email': forms.EmailInput(attrs={'class': 'sv-form-input'}),
            'username': forms.TextInput(attrs={'class': 'sv-form-input'}),
            'role': forms.Select(attrs={'class': 'sv-form-input sv-form-select'}),
            'institution': forms.TextInput(attrs={'class': 'sv-form-input'}),
            'department': forms.TextInput(attrs={'class': 'sv-form-input'}),
            'research_area': forms.TextInput(attrs={'class': 'sv-form-input'}),
        }


class PublicationForm(forms.ModelForm):
    class Meta:
        model = Publication
        fields = [
            'title', 'author', 'co_authors', 'abstract', 'category', 'publication_type',
            'publication_year', 'publisher', 'journal_name', 'volume', 'issue', 'pages',
            'doi', 'isbn', 'file', 'cover_image', 'external_url', 'is_open_access',
            'is_published', 'institution', 'language', 'keywords',
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'author': forms.TextInput(attrs={'class': 'form-control'}),
            'co_authors': forms.TextInput(attrs={'class': 'form-control'}),
            'abstract': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'publication_type': forms.Select(attrs={'class': 'form-select'}),
            'publication_year': forms.NumberInput(attrs={'class': 'form-control', 'min': 1900, 'max': 2030}),
            'publisher': forms.TextInput(attrs={'class': 'form-control'}),
            'journal_name': forms.TextInput(attrs={'class': 'form-control'}),
            'volume': forms.TextInput(attrs={'class': 'form-control'}),
            'issue': forms.TextInput(attrs={'class': 'form-control'}),
            'pages': forms.TextInput(attrs={'class': 'form-control'}),
            'doi': forms.TextInput(attrs={'class': 'form-control'}),
            'isbn': forms.TextInput(attrs={'class': 'form-control'}),
            'external_url': forms.URLInput(attrs={'class': 'form-control'}),
            'institution': forms.TextInput(attrs={'class': 'form-control'}),
            'language': forms.TextInput(attrs={'class': 'form-control'}),
            'keywords': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'machine learning, AI, deep learning'}),
            'file': forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'}),
            'cover_image': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }
