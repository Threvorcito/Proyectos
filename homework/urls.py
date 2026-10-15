from django.urls import path

from . import views_teacher

app_name = 'homework'

urlpatterns = [
    path('', views_teacher.task_list, name='task_list'),
    path('nueva/', views_teacher.task_create, name='task_create'),
    path('<int:pk>/', views_teacher.task_detail, name='task_detail'),
    path('<int:pk>/editar/', views_teacher.task_update, name='task_update'),
    path('<int:pk>/alumnos/', views_teacher.task_assign, name='task_assign'),
    path('<int:pk>/pasos/nuevo/<slug:step_type>/', views_teacher.step_create, name='step_create'),
    path('<int:pk>/pasos/<int:step_pk>/editar/', views_teacher.step_update, name='step_update'),
    path('<int:pk>/pasos/<int:step_pk>/eliminar/', views_teacher.step_delete, name='step_delete'),
    path('<int:pk>/pasos/<int:step_pk>/mover/', views_teacher.step_move, name='step_move'),
    path('<int:pk>/duplicar/', views_teacher.task_duplicate, name='task_duplicate'),
    path('<int:pk>/archivar/', views_teacher.task_archive, name='task_archive'),
]
