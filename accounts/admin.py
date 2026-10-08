from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'matricule', 'nom', 'prenom', 'role', 'statut', 'is_staff')
    list_filter = ('role', 'statut', 'is_staff')
    search_fields = ('email', 'nom', 'prenom', 'matricule')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Identité', {'fields': ('matricule', 'nom', 'prenom', 'telephone', 'photo')}),
        ('Rôles', {'fields': ('role', 'statut', 'is_active', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('derniere_connexion', 'date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'nom', 'prenom', 'role', 'password1', 'password2'),
        }),
    )
