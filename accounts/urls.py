from django.urls import path

from .views import ProfileView, RegisterView, UserLoginView, UserLogoutView, student_access_key, student_access_parents, student_access_students, student_access_code

app_name = 'accounts'

urlpatterns = [
    path('registro/', RegisterView.as_view(), name='register'),
    path('estudiantes/', student_access_code, name='student_access'),
    path('estudiantes/alumnos/', student_access_students, name='student_access_students'),
    path('estudiantes/tutores/', student_access_parents, name='student_access_parents'),
    path('estudiantes/dibujos/', student_access_key, name='student_access_key'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('perfil/', ProfileView.as_view(), name='profile'),
]
