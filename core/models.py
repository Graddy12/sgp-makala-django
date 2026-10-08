from django.conf import settings
from django.db import models


class TypeNotification(models.TextChoices):
    INFO = 'info', 'Info'
    WARNING = 'warning', 'Warning'
    DANGER = 'danger', 'Danger'
    SUCCESS = 'success', 'Success'


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs'
    )
    user_nom = models.CharField(max_length=150, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    action = models.CharField(max_length=100)
    module = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.CharField(max_length=45)
    user_agent = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action} — {self.module}'


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='notifications'
    )
    titre = models.CharField(max_length=150)
    message = models.TextField()
    type = models.CharField(
        max_length=20, choices=TypeNotification.choices, default=TypeNotification.INFO
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return self.titre
