from django.urls import path

from . import views

app_name = 'games'

urlpatterns = [
    path('', views.games_index, name='index'),
    path('<slug:slug>/', views.game_detail, name='detail'),
    path('<slug:slug>/guardar/', views.save_attempt, name='save_attempt'),
]
