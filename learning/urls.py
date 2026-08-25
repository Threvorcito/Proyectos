from django.urls import path

from . import views
from .views_accessibility import accessibility_settings

app_name = 'learning'

urlpatterns = [
    path('', views.level_list, name='levels'),
    path('nivel/<int:number>/', views.level_detail, name='level_detail'),
    path('mi-forma-de-leer/', accessibility_settings, name='accessibility'),
]
