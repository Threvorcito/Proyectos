from django.urls import path

from . import views

app_name = 'readings'

urlpatterns = [
    path('', views.reading_list, name='list'),
    path('<int:pk>/', views.reading_detail, name='detail'),
]
