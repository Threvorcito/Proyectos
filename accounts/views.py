from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile

from .forms import ProfileUpdateForm, RegistrationForm, StudentProfileForm
from .models import CustomUser


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_name'] = 'Lectura sin Límites'
        return context

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['username'].label = 'Nombre de usuario'
        form.fields['username'].widget.attrs.update({
            'class': 'login-page__input',
            'placeholder': 'Escribe tu usuario',
            'autocomplete': 'username',
        })
        form.fields['password'].label = 'Contraseña'
        form.fields['password'].widget.attrs.update({
            'class': 'login-page__input',
            'placeholder': 'Escribe tu contraseña',
            'autocomplete': 'current-password',
        })
        return form


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('core:home')


class RegisterView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('dashboard:redirect')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = form.cleaned_data['role']
        user.email = form.cleaned_data['email']
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        user.save()
        level = Level.objects.filter(number=form.cleaned_data.get('reading_level') or 1).first()
        if user.role == CustomUser.Role.STUDENT:
            StudentProfile.objects.get_or_create(
                user=user,
                defaults={
                    'name': f'{user.first_name} {user.last_name}'.strip(),
                    'grade': form.cleaned_data.get('grade') or '1',
                    'reading_level': level,
                    'current_level': level,
                },
            )
        elif user.role == CustomUser.Role.TEACHER:
            TeacherProfile.objects.get_or_create(user=user, defaults={'name': f'{user.first_name} {user.last_name}'.strip()})
        elif user.role == CustomUser.Role.PARENT:
            ParentProfile.objects.get_or_create(user=user, defaults={'name': f'{user.first_name} {user.last_name}'.strip()})
        login(self.request, user)
        messages.success(self.request, 'Cuenta creada correctamente.')
        return super().form_valid(form)


class ProfileView(UpdateView):
    model = CustomUser
    form_class = ProfileUpdateForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('dashboard:redirect')

    def get_object(self, queryset=None):
        return self.request.user
