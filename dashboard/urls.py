from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.redirect_after_login, name='redirect'),
    path('admin/', views.admin_dashboard, name='admin'),
    path('admin/gestion/<slug:resource>/', views.admin_resource_landing, name='admin_resource'),
    path('admin/gestion/<slug:resource>/nuevo/', views.admin_resource_create, name='admin_resource_create'),
    path('admin/gestion/<slug:resource>/<int:pk>/editar/', views.admin_resource_update, name='admin_resource_update'),
    path('alumnos/nuevo/', views.quick_student_create, name='quick_student_create'),
    path('planes/', views.lesson_plan_list, name='lesson_plans'),
    path('planes/nuevo/', views.lesson_plan_create, name='lesson_plan_create'),
    path('planes/<int:pk>/editar/', views.lesson_plan_update, name='lesson_plan_update'),
    path('estudiante/<int:pk>/reporte/', views.student_report, name='student_report'),
    path('estudiante/', views.student_dashboard, name='student'),
    path('docente/', views.teacher_dashboard, name='teacher'),
    path('padres/', views.parent_dashboard, name='parents'),
]
