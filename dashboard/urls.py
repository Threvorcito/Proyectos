from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.redirect_after_login, name='redirect'),
    path('estudiante/', views.student_dashboard, name='student'),
    path('docente/', views.teacher_dashboard, name='teacher'),
    path('padres/', views.parent_dashboard, name='parents'),
]
