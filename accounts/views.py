import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import FormView, UpdateView

from activities.models import Activity
from games.models import Game
from readings.models import Reading
from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile
from learning.models import LessonPlan

from . import lockout
from .forms import EmailAuthenticationForm, ProfileUpdateForm, RegistrationForm, StudentProfileForm
from .models import CustomUser


CLASSROOM_COOKIE = 'classroom'
CLASSROOM_COOKIE_SALT = 'accounts.classroom'
CLASSROOM_COOKIE_MAX_AGE = 60 * 60 * 24 * 30
CLASSROOM_CODE_MAX_FAILURES = 20
LOCKED_CHILD_MESSAGE = 'Hiciste muchos intentos. Pide ayuda a tu docente y prueba en un ratito.'
KEY_REST_MESSAGE = 'Vamos a descansar un ratito. Pide ayuda a tu maestra.'
KEY_TEACHER_MESSAGE = 'Pide ayuda a tu maestra.'
# A 2-of-9 key has only 36 combinations: count misses over a whole day and
# escalate repeated lockouts to the teacher (see accounts.lockout).
STUDENT_KEY_FAILURE_WINDOW = timedelta(hours=24)


def _clear_student_access_session(request):
    for key in ('student_access_teacher_id', 'student_access_student_id', 'student_access_parent_id'):
        request.session.pop(key, None)


def _classroom_teacher(teacher_id, code):
    if not teacher_id or not code:
        return None
    return TeacherProfile.objects.filter(pk=teacher_id, classroom_code=code, is_active=True).first()


def _student_access_teacher(request):
    """Return the teacher unlocked on this device with a valid classroom code."""
    return _classroom_teacher(
        request.session.get('student_access_teacher_id'),
        request.session.get('student_access_classroom_code'),
    )


def _remembered_classroom_teacher(request):
    value = request.get_signed_cookie(
        CLASSROOM_COOKIE, default='', salt=CLASSROOM_COOKIE_SALT, max_age=CLASSROOM_COOKIE_MAX_AGE,
    )
    teacher_id, _, code = (value or '').partition(':')
    return _classroom_teacher(teacher_id if teacher_id.isdigit() else None, code)


def _unlock_classroom(request, teacher):
    _clear_student_access_session(request)
    request.session['student_access_teacher_id'] = teacher.pk
    request.session['student_access_classroom_code'] = teacher.classroom_code


def _client_ip(request):
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def _student_access_student(request, teacher):
    student_id = request.session.get('student_access_student_id')
    if not student_id or teacher is None:
        return None
    return teacher.students.select_related('user').filter(pk=student_id, user__is_active=True).first()


def student_access_code(request):
    """Public entry: a classroom code unlocks one teacher's roster on this device."""
    if request.method == 'POST':
        if request.POST.get('forget'):
            _clear_student_access_session(request)
            request.session.pop('student_access_classroom_code', None)
            response = redirect('accounts:student_access')
            response.delete_cookie(CLASSROOM_COOKIE)
            return response

        lock_key = f'classroom-ip:{_client_ip(request)}'
        if lockout.is_locked(lock_key):
            messages.error(request, LOCKED_CHILD_MESSAGE)
            return redirect('accounts:student_access')
        code = TeacherProfile.normalize_classroom_code(request.POST.get('code'))
        teacher = TeacherProfile.objects.filter(classroom_code=code, is_active=True).first() if code else None
        if teacher is None:
            # Never reset this key on success: a known code must not refill guesses.
            lockout.register_failure(lock_key, max_failures=CLASSROOM_CODE_MAX_FAILURES)
            messages.error(request, 'Ese código no es correcto. Revisa las letras con tu docente.')
            return redirect('accounts:student_access')
        _unlock_classroom(request, teacher)
        response = redirect('accounts:student_access_students')
        response.set_signed_cookie(
            CLASSROOM_COOKIE,
            f'{teacher.pk}:{teacher.classroom_code}',
            salt=CLASSROOM_COOKIE_SALT,
            max_age=CLASSROOM_COOKIE_MAX_AGE,
            httponly=True,
            samesite='Lax',
            secure=settings.SESSION_COOKIE_SECURE,
        )
        return response

    teacher = _student_access_teacher(request) or _remembered_classroom_teacher(request)
    if teacher is not None:
        _unlock_classroom(request, teacher)
        return redirect('accounts:student_access_students')
    return render(request, 'accounts/student_access_code.html')


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
        return redirect('accounts:student_access_key')

    students = list(teacher.students.select_related('user', 'current_level').filter(user__is_active=True).order_by('name'))
    name_counts = {}
    for student in students:
        name_counts[student.display_name()] = name_counts.get(student.display_name(), 0) + 1
    duplicate_names = {name for name, count in name_counts.items() if count > 1}
    return render(request, 'accounts/student_access_students.html', {'teacher': teacher, 'students': students, 'duplicate_names': duplicate_names})


def student_access_parents(request):
    """Old tutor step: children no longer pick a tutor, so go on to the drawings."""
    request.session.pop('student_access_parent_id', None)
    return redirect('accounts:student_access_key')


def _key_locked_redirect(request, lock_key):
    request.session.pop('student_access_student_id', None)
    messages.info(request, KEY_TEACHER_MESSAGE if lockout.needs_unlock(lock_key) else KEY_REST_MESSAGE)
    return redirect('accounts:student_access_students')


def _submitted_key(request, student):
    if student.has_pair_visual_key:
        return request.POST.getlist('symbols')
    return [request.POST.get(f'symbol_{index}', '') for index in range(1, student.VISUAL_KEY_LEGACY_SIZE + 1)]


def student_access_key(request):
    teacher = _student_access_teacher(request)
    student = _student_access_student(request, teacher)
    if teacher is None or student is None:
        return redirect('accounts:student_access')
    if not student.visual_key_hash:
        messages.info(request, 'Pide a tu maestra que cree tus dibujos secretos.')
        return redirect('accounts:student_access_students')

    lock_key = lockout.student_key(student.pk)
    if lockout.is_locked(lock_key):
        return _key_locked_redirect(request, lock_key)
    try_again = False
    if request.method == 'POST':
        if student.check_visual_key(_submitted_key(request, student)):
            lockout.reset(lock_key)
            _clear_student_access_session(request)
            login(request, student.user, backend='django.contrib.auth.backends.ModelBackend')
            request.session['kid_signin_cheer'] = True
            messages.success(request, '¡Muy bien! Vamos a aprender.')
            return redirect('dashboard:student')
        lockout.register_failure(
            lock_key, escalate_after=lockout.ESCALATE_AFTER, window=STUDENT_KEY_FAILURE_WINDOW,
        )
        if lockout.is_locked(lock_key):
            return _key_locked_redirect(request, lock_key)
        try_again = True

    choices = StudentProfile.visual_key_items()
    random_choices = secrets.SystemRandom().sample(choices, len(choices))
    return render(request, 'accounts/student_access_key.html', {
        'teacher': teacher,
        'student': student,
        'choices': random_choices,
        'pair_key': student.has_pair_visual_key,
        'pair_size': StudentProfile.VISUAL_KEY_PAIR_SIZE,
        'steps': range(1, StudentProfile.VISUAL_KEY_LEGACY_SIZE + 1),
        'try_again': try_again,
    }, status=200)


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
    # Register is for adults (teachers and families): skip the child layer and mascot.
    extra_context = {'adult_layout': True}

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


class ProfileView(LoginRequiredMixin, UpdateView):
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
            activities = Activity.objects.filter(is_active=True).select_related('subject', 'level').order_by('-created_at')[:6]
            games = Game.objects.filter(is_active=True).select_related('subject', 'level').order_by('grade', 'name')[:6]
            readings = Reading.objects.filter(is_active=True).select_related('subject', 'level').order_by('grade', 'title')[:6]
            context.update({
                'teacher_profile': teacher,
                'teacher_lesson_plans': lesson_plans,
                'teacher_activities': activities,
                'teacher_games': games,
                'teacher_readings': readings,
                'teacher_report_stats': {
                    'plans': LessonPlan.objects.filter(teacher=teacher).count(),
                    'activities': Activity.objects.filter(is_active=True).count(),
                    'games': Game.objects.filter(is_active=True).count(),
                    'readings': Reading.objects.filter(is_active=True).count(),
                },
            })
        return context
