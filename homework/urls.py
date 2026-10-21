from django.urls import path

from . import views_student, views_teacher

app_name = 'homework'

urlpatterns = [
    path('', views_teacher.task_list, name='task_list'),
    path('nueva/', views_teacher.task_create, name='task_create'),
    path('secuencia-fas/', views_teacher.fas_sequence, name='fas_sequence'),
    path('secuencia-fas/<str:letter>/crear/', views_teacher.fas_class_create, name='fas_class_create'),
    path('<int:pk>/', views_teacher.task_detail, name='task_detail'),
    path('<int:pk>/editar/', views_teacher.task_update, name='task_update'),
    path('<int:pk>/alumnos/', views_teacher.task_assign, name='task_assign'),
    path('<int:pk>/pasos/nuevo/<slug:step_type>/', views_teacher.step_create, name='step_create'),
    path('<int:pk>/pasos/<int:step_pk>/editar/', views_teacher.step_update, name='step_update'),
    path('<int:pk>/pasos/<int:step_pk>/eliminar/', views_teacher.step_delete, name='step_delete'),
    path('<int:pk>/pasos/<int:step_pk>/mover/', views_teacher.step_move, name='step_move'),
    path('<int:pk>/duplicar/', views_teacher.task_duplicate, name='task_duplicate'),
    path('<int:pk>/vista-previa/', views_teacher.task_preview, name='task_preview'),
    path('<int:pk>/archivar/', views_teacher.task_archive, name='task_archive'),
    path('<int:pk>/reporte/', views_teacher.task_report, name='task_report'),
    path('<int:pk>/dictado/<int:step_pk>/instrumento/', views_teacher.dictation_instrument, name='dictation_instrument'),
    path('seguimiento/<int:assignment_pk>/', views_teacher.assignment_report, name='assignment_report'),
    path('seguimiento/<int:assignment_pk>/nivel/', views_teacher.assignment_level_update, name='assignment_level_update'),
    path('mi-tarea/<int:assignment_pk>/', views_student.student_task, name='student_task'),
    path('mi-tarea/<int:assignment_pk>/paso/<int:order>/', views_student.student_step, name='student_step'),
    path('mi-tarea/<int:assignment_pk>/paso/<int:order>/listo/', views_student.step_done, name='step_done'),
    path('mi-tarea/<int:assignment_pk>/paso/<int:order>/responder/', views_student.step_answer, name='step_answer'),
    path('mi-tarea/<int:assignment_pk>/ayuda/', views_student.decode_help, name='decode_help'),
]
