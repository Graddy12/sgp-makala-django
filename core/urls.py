from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('health/', views.health, name='health'),
    path('', views.dashboard, name='dashboard'),
    path('reports/', views.reports, name='reports'),
    path('reports/pdf/', views.reports_pdf, name='reports_pdf'),
    path('audit/', views.audit_list, name='audit'),
    path('backup/', views.backup_page, name='backup'),
    path('backup/export/', views.backup_export, name='backup_export'),
    path('media/photo/<str:filename>/', views.media_photo, name='media_photo'),
    path('media/document/<str:filename>/', views.media_document, name='media_document'),
    path('403/', views.forbidden, name='forbidden'),
]
