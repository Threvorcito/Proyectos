from django.urls import path

from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    path('privacidad/', views.privacy, name='privacy'),
    path('404-preview/', views.error_preview, name='error_preview'),
]
