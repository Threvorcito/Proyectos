from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from activities.models import Activity
from games.models import Game
from readings.models import Reading
from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile
from learning.models import Lesson, LessonPlan

from .forms import EmailAuthenticationForm, ProfileUpdateForm, RegistrationForm, StudentProfileForm
from .models import CustomUser


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = EmailAuthenticationForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['site_name'] = 'Lectura sin Límites'
        return context

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = getattr(self.request.user, 'teacher_profile', None)
        if teacher is not None:
            lesson_plans = LessonPlan.objects.filter(teacher=teacher).select_related('subject', 'level').prefetch_related('activities', 'readings')[:6]
            lessons = Lesson.objects.filter(is_active=True).select_related('level').order_by('level__order', 'order')[:6]
            activities = Activity.objects.filter(is_active=True).select_related('subject', 'level').order_by('-created_at')[:6]
            games = Game.objects.filter(is_active=True).select_related('subject', 'level').order_by('grade', 'name')[:6]
            readings = Reading.objects.filter(is_active=True).select_related('subject', 'level').order_by('grade', 'title')[:6]
            context.update({
                'teacher_profile': teacher,
                'teacher_lesson_plans': lesson_plans,
                'teacher_lessons': lessons,
                'teacher_activities': activities,
                'teacher_games': games,
                'teacher_readings': readings,
                'teacher_report_stats': {
                    'plans': LessonPlan.objects.filter(teacher=teacher).count(),
                    'lessons': Lesson.objects.filter(is_active=True).count(),
                    'activities': Activity.objects.filter(is_active=True).count(),
                    'games': Game.objects.filter(is_active=True).count(),
                    'readings': Reading.objects.filter(is_active=True).count(),
                },
            })
        return context
