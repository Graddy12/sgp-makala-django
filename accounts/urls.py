from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/password/', views.profile_password, name='profile_password'),
    path('users/', views.users_list, name='users'),
    path('users/create/', views.users_create, name='users_create'),
    path('users/<int:pk>/toggle/', views.users_toggle, name='users_toggle'),
]
