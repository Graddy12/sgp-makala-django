from django.contrib import admin
from .models import AuditLog, Notification


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'module', 'user_nom', 'ip_address', 'created_at')
    list_filter = ('module', 'action')
    search_fields = ('description', 'user_nom')
    readonly_fields = [f.name for f in AuditLog._meta.fields]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('titre', 'type', 'user', 'is_read', 'created_at')
    list_filter = ('type', 'is_read')
