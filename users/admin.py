from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'username', 'full_name', 'role', 'institution', 'is_verified', 'date_joined']
    list_filter = ['role', 'is_phd_student', 'is_verified', 'is_staff']
    search_fields = ['email', 'username', 'first_name', 'last_name', 'institution']
    ordering = ['-date_joined']
    
    fieldsets = BaseUserAdmin.fieldsets + (
        ('PhD Library Profile', {
            'fields': ('role', 'is_phd_student', 'institution', 'department', 'research_area', 'bio', 'avatar', 'is_verified')
        }),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('PhD Library Profile', {
            'fields': ('email', 'role', 'institution', 'research_area')
        }),
    )
