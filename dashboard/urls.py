from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.redirect_after_login, name='redirect'),
    path('admin/', views.admin_dashboard, name='admin'),
    path('admin/gestion/<slug:resource>/', views.admin_resource_landing, name='admin_resource'),
    path('admin/gestion/<slug:resource>/nuevo/', views.admin_resource_create, name='admin_resource_create'),
    path('admin/gestion/<slug:resource>/<int:pk>/editar/', views.admin_resource_update, name='admin_resource_update'),
    path('admin/gestion/<slug:resource>/<int:pk>/eliminar/', views.admin_resource_delete, name='admin_resource_delete'),
    path('admin/profesores/<int:pk>/permisos/', views.teacher_permissions_update, name='teacher_permissions_update'),
    path('docente/gestion/<slug:resource>/', views.admin_resource_landing, name='teacher_resource'),
    path('docente/gestion/<slug:resource>/nuevo/', views.admin_resource_create, name='teacher_resource_create'),
    path('docente/gestion/<slug:resource>/<int:pk>/editar/', views.admin_resource_update, name='teacher_resource_update'),
    path('docente/gestion/<slug:resource>/<int:pk>/eliminar/', views.admin_resource_delete, name='teacher_resource_delete'),
    path('docente/alumnos/', views.teacher_students, name='teacher_students'),
    path('docente/alumnos/<int:pk>/entrar/', views.teacher_student_login, name='teacher_student_login'),
    path('docente/alumnos/<int:pk>/dibujos/', views.teacher_student_visual_key_regenerate, name='teacher_student_visual_key_regenerate'),
    path('docente/alumnos/<int:pk>/editar/', views.teacher_student_update, name='teacher_student_update'),
    path('docente/alumnos/<int:pk>/eliminar/', views.teacher_student_delete, name='teacher_student_delete'),
    path('alumnos/nuevo/', views.quick_student_create, name='quick_student_create'),
    path('planes/', views.lesson_plan_list, name='lesson_plans'),
    path('planes/nuevo/', views.lesson_plan_create, name='lesson_plan_create'),
    path('planes/<int:pk>/implementar/', views.lesson_plan_implementation, name='lesson_plan_implementation'),
    path('planes/<int:pk>/reporte/', views.lesson_plan_report, name='lesson_plan_report'),
    path('planes/<int:pk>/seguimiento/<int:assignment_pk>/', views.lesson_plan_assignment_update, name='lesson_plan_assignment_update'),
    path('planes/<int:pk>/editar/', views.lesson_plan_update, name='lesson_plan_update'),
    path('estudiante/<int:pk>/reporte/', views.student_report, name='student_report'),
    path('estudiante/planes/<int:pk>/', views.student_lesson_plan, name='student_lesson_plan'),
    path('estudiante/', views.student_dashboard, name='student'),
    path('docente/', views.teacher_dashboard, name='teacher'),
    path('padres/', views.parent_dashboard, name='parents'),
]
