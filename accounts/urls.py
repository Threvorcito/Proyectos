from django.urls import path

from .views import ProfileView, RegisterView, UserLoginView, UserLogoutView

app_name = 'accounts'

urlpatterns = [
    path('registro/', RegisterView.as_view(), name='register'),
    path('login/', UserLoginView.as_view(), name='login'),
    path('logout/', UserLogoutView.as_view(), name='logout'),
    path('perfil/', ProfileView.as_view(), name='profile'),
]
