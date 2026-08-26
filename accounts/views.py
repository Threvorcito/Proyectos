import secrets

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


def _clear_student_access_session(request):
    for key in ('student_access_teacher_id', 'student_access_student_id', 'student_access_parent_id', 'student_access_attempts'):
        request.session.pop(key, None)


def _student_access_teacher(request):
    teacher_id = request.session.get('student_access_teacher_id')
    if not teacher_id:
        return None
    return TeacherProfile.objects.filter(pk=teacher_id, is_active=True, students__user__is_active=True).distinct().first()


def _student_access_student(request, teacher):
    student_id = request.session.get('student_access_student_id')
    if not student_id or teacher is None:
        return None
    return teacher.students.select_related('user').filter(pk=student_id, user__is_active=True).first()


def _student_access_parent(request, student):
    parent_id = request.session.get('student_access_parent_id')
    if not parent_id or student is None:
        return None
    return ParentProfile.objects.filter(pk=parent_id, students=student, user__is_active=True).first()


def student_access_teachers(request):
    if request.method == 'POST':
        teacher = TeacherProfile.objects.filter(
            pk=request.POST.get('teacher_id'),
            is_active=True,
            students__user__is_active=True,
        ).distinct().first()
        if teacher is None:
            messages.error(request, 'Escoge una profe o un profe de la lista.')
            return redirect('accounts:student_access')
        _clear_student_access_session(request)
        request.session['student_access_teacher_id'] = teacher.pk
        return redirect('accounts:student_access_students')

    teachers = TeacherProfile.objects.filter(is_active=True, students__user__is_active=True).distinct().order_by('name')
    return render(request, 'accounts/student_access_teachers.html', {'teachers': teachers})


def student_access_students(request):
    teacher = _student_access_teacher(request)
    if teacher is None:
        return redirect('accounts:student_access')

    if request.method == 'POST':
        student = teacher.students.select_related('user').filter(pk=request.POST.get('student_id'), user__is_active=True).first()
        if student is None:
            messages.error(request, 'Escoge tu tarjeta de la lista.')
            return redirect('accounts:student_access_students')
        request.session['student_access_student_id'] = student.pk
        request.session.pop('student_access_parent_id', None)
        request.session['student_access_attempts'] = 0
        return redirect('accounts:student_access_parents')

    students = list(teacher.students.select_related('user', 'current_level').filter(user__is_active=True).order_by('name'))
    name_counts = {}
    for student in students:
        name_counts[student.display_name()] = name_counts.get(student.display_name(), 0) + 1
    duplicate_names = {name for name, count in name_counts.items() if count > 1}
    return render(request, 'accounts/student_access_students.html', {'teacher': teacher, 'students': students, 'duplicate_names': duplicate_names})


def student_access_parents(request):
    teacher = _student_access_teacher(request)
    student = _student_access_student(request, teacher)
    if teacher is None or student is None:
        return redirect('accounts:student_access')

    if request.method == 'POST':
        parent = ParentProfile.objects.filter(pk=request.POST.get('parent_id'), students=student, user__is_active=True).first()
        if parent is None:
            messages.error(request, 'Escoge quién te acompaña en casa.')
            return redirect('accounts:student_access_parents')
        request.session['student_access_parent_id'] = parent.pk
        return redirect('accounts:student_access_key')

    parents = ParentProfile.objects.filter(students=student, user__is_active=True).select_related('user').order_by('name')
    return render(request, 'accounts/student_access_parents.html', {'teacher': teacher, 'student': student, 'parents': parents})


def student_access_key(request):
    teacher = _student_access_teacher(request)
    student = _student_access_student(request, teacher)
    parent = _student_access_parent(request, student)
    if teacher is None or student is None or parent is None:
        return redirect('accounts:student_access')
    if not student.visual_key_hash:
        messages.error(request, 'Pide a tu docente que cree tus dibujos secretos.')
        return redirect('accounts:student_access_students')

    if request.method == 'POST':
        selected_codes = [request.POST.get(f'symbol_{index}', '') for index in range(1, 4)]
        if student.check_visual_key(selected_codes):
            _clear_student_access_session(request)
            login(request, student.user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, '¡Muy bien! Vamos a aprender.')
            return redirect('dashboard:student')
        attempts = int(request.session.get('student_access_attempts', 0)) + 1
        request.session['student_access_attempts'] = attempts
        if attempts >= 5:
            _clear_student_access_session(request)
            messages.error(request, 'Vamos a intentarlo de nuevo desde el inicio.')
            return redirect('accounts:student_access')
        messages.error(request, 'Intenta otra vez con tus dibujos secretos.')

    choices = StudentProfile.visual_key_items()
    random_choices = secrets.SystemRandom().sample(choices, len(choices))
    return render(request, 'accounts/student_access_key.html', {
        'teacher': teacher,
        'student': student,
        'parent': parent,
        'choices': random_choices,
        'steps': (1, 2, 3),
    })


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
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
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
