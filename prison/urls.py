from django.urls import path
from . import views

app_name = 'prison'

urlpatterns = [
    path('detenus/', views.detenus_list, name='detenus'),
    path('detenus/create/', views.detenus_create, name='detenus_create'),
    path('detenus/<int:pk>/', views.detenus_show, name='detenus_show'),
    path('detenus/<int:pk>/edit/', views.detenus_edit, name='detenus_edit'),
    path('detenus/<int:pk>/archive/', views.detenus_archive, name='detenus_archive'),
    path('detenus/<int:pk>/print/', views.detenus_print, name='detenus_print'),

    path('cellules/', views.cellules_list, name='cellules'),
    path('cellules/create/', views.cellules_create, name='cellules_create'),
    path('cellules/<int:pk>/', views.cellules_show, name='cellules_show'),

    path('jugements/', views.jugements_list, name='jugements'),
    path('jugements/create/', views.jugements_create, name='jugements_create'),

    path('transferts/', views.transferts_list, name='transferts'),
    path('transferts/create/', views.transferts_create, name='transferts_create'),
    path('transferts/<int:pk>/status/', views.transferts_status, name='transferts_status'),

    path('visites/', views.visites_list, name='visites'),
    path('visites/create/', views.visites_create, name='visites_create'),
    path('visites/<int:pk>/end/', views.visites_end, name='visites_end'),

    path('documents/', views.documents_list, name='documents'),
    path('documents/store/', views.documents_store, name='documents_store'),
]
