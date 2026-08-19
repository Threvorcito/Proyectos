from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from activities.models import Activity
from activities.services import get_recommended_activities
from gamification.services import evaluate_achievements
from games.models import Game
from learning.models import Lesson, LessonPlan, Level, ParentProfile, StudentProfile, Subject, Syllable, TeacherProfile, Word
from progress.models import StudentDifficulty, StudentProgress
from readings.models import Reading

from .forms import AdminUserCreationForm, LessonPlanForm, QuickStudentCreationForm, TeacherCreationForm, build_admin_model_form, style_admin_form


ADMIN_RESOURCES = {
    'usuarios': {'title': 'Usuarios y roles', 'singular': 'usuario', 'model': CustomUser, 'form': AdminUserCreationForm, 'fields': None},
    'profesores': {'title': 'Profesores', 'singular': 'profesor', 'model': TeacherProfile, 'create_form': TeacherCreationForm, 'fields': ('user', 'name', 'bio', 'can_manage_lessons', 'can_manage_activities', 'can_manage_readings')},
    'alumnos': {'title': 'Alumnos', 'singular': 'alumno', 'model': StudentProfile, 'create_form': QuickStudentCreationForm, 'fields': ('user', 'name', 'alias', 'birth_date', 'grade', 'reading_level', 'current_level', 'points', 'stars')},
    'padres': {'title': 'Padres o tutores', 'singular': 'tutor', 'model': ParentProfile, 'fields': ('user', 'name')},
    'niveles': {'title': 'Niveles', 'singular': 'nivel', 'model': Level, 'fields': ('number', 'name', 'description', 'order', 'is_active')},
    'materias': {'title': 'Materias', 'singular': 'materia', 'model': Subject, 'fields': ('name', 'description', 'is_active')},
    'clases': {'title': 'Clases', 'singular': 'clase', 'model': Lesson, 'fields': ('level', 'title', 'description', 'stage', 'order', 'is_active')},
    'actividades': {'title': 'Actividades', 'singular': 'actividad', 'model': Activity, 'fields': ('subject', 'grade', 'level', 'title', 'description', 'instructions', 'activity_type', 'difficulty', 'points', 'stars', 'is_active')},
    'lecturas': {'title': 'Lecturas', 'singular': 'lectura', 'model': Reading, 'fields': ('subject', 'grade', 'title', 'description', 'content', 'image', 'level', 'difficulty', 'estimated_time', 'audio_optional', 'is_active')},
    'juegos': {'title': 'Juegos', 'singular': 'juego', 'model': Game, 'fields': ('subject', 'grade', 'name', 'slug', 'description', 'skill', 'game_type', 'level', 'icon', 'is_active')},
    'palabras': {'title': 'Palabras', 'singular': 'palabra', 'model': Word, 'fields': ('text', 'image', 'level', 'syllables')},
    'silabas': {'title': 'Sílabas', 'singular': 'sílaba', 'model': Syllable, 'fields': ('text', 'level')},
}


def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'


def is_admin_user(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_staff or user.is_superuser)


def is_parent(user):
    return user.is_authenticated and user.role == 'PARENT'


def is_teacher_or_admin(user):
    return user.is_authenticated and (user.role in ('TEACHER', 'ADMIN') or user.is_staff or user.is_superuser)


def can_manage_resource(user, resource):
    if is_admin_user(user):
        return True
    teacher = getattr(user, 'teacher_profile', None)
    if not user.is_authenticated or user.role != 'TEACHER' or teacher is None:
        return False
    permission_map = {
        'clases': teacher.can_manage_lessons,
        'actividades': teacher.can_manage_activities,
        'lecturas': teacher.can_manage_readings,
    }
    return permission_map.get(resource, False)


@login_required
def redirect_after_login(request):
    role = getattr(request.user, 'role', 'STUDENT')
    if role == 'ADMIN' or request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard:admin')
    if role == 'TEACHER':
        return redirect('dashboard:teacher')
    if role == 'PARENT':
        return redirect('dashboard:parents')
    return redirect('dashboard:student')


@login_required
@user_passes_test(is_admin_user)
def admin_dashboard(request):
    stats = {
        'users': CustomUser.objects.count(),
        'teachers': TeacherProfile.objects.count(),
        'students': StudentProfile.objects.count(),
        'parents': ParentProfile.objects.count(),
        'levels': Level.objects.count(),
        'lessons': Lesson.objects.count(),
        'subjects': Subject.objects.count(),
        'lesson_plans': LessonPlan.objects.count(),
        'activities': Activity.objects.count(),
        'readings': Reading.objects.count(),
        'games': Game.objects.count(),
    }
    recent_students = StudentProfile.objects.select_related('user', 'current_level').order_by('-created_at')[:5]
    return render(request, 'dashboard/admin_dashboard.html', {'stats': stats, 'recent_students': recent_students, 'resources': ADMIN_RESOURCES})


@login_required
def admin_resource_landing(request, resource):
    config = ADMIN_RESOURCES.get(resource)
    if not config:
        messages.error(request, 'El recurso solicitado no existe.')
        return redirect('dashboard:admin')
    if not can_manage_resource(request.user, resource):
        messages.error(request, 'No tienes permiso para gestionar este recurso.')
        return redirect('dashboard:redirect')
    objects = config['model'].objects.all()
    if resource == 'usuarios':
        objects = objects.filter(is_superuser=False)
    objects = objects.order_by('-pk')[:20]
    create_form = None
    if resource in ('usuarios', 'profesores', 'alumnos'):
        form_class = config.get('create_form') or config.get('form') or build_admin_model_form(config['model'], config['fields'])
        create_form = style_admin_form(form_class())
    return render(request, 'dashboard/admin_resource_landing.html', {
        'resource': resource,
        'config': config,
        'objects': objects,
        'create_form': create_form,
    })


@login_required
def admin_resource_create(request, resource):
    config = ADMIN_RESOURCES.get(resource)
    if not config:
        messages.error(request, 'El recurso solicitado no existe.')
        return redirect('dashboard:admin')
    if not can_manage_resource(request.user, resource):
        messages.error(request, 'No tienes permiso para crear este recurso.')
        return redirect('dashboard:redirect')
    form_class = config.get('create_form') or config.get('form') or build_admin_model_form(config['model'], config['fields'])
    form = style_admin_form(form_class(request.POST or None, request.FILES or None))
    credentials = None
    if request.method == 'POST' and form.is_valid():
        form.save()
        credentials = getattr(form, 'created_credentials', None)
        messages.success(request, f"Se agregó correctamente el {config['singular']}.")
        if request.POST.get('_from_modal'):
            if credentials:
                messages.success(request, f"Credenciales creadas - Usuario: {credentials['username']} / Contraseña: {credentials['password']}")
            return redirect('dashboard:admin_resource', resource=resource)
        if credentials is None:
            return redirect('dashboard:admin_resource', resource=resource)
        form = form_class()
    return render(request, 'dashboard/admin_resource_form.html', {'resource': resource, 'config': config, 'form': form, 'is_edit': False, 'credentials': credentials})


@login_required
def admin_resource_update(request, resource, pk):
    config = ADMIN_RESOURCES.get(resource)
    if not config:
        messages.error(request, 'El recurso solicitado no existe.')
        return redirect('dashboard:admin')
    if not can_manage_resource(request.user, resource):
        messages.error(request, 'No tienes permiso para editar este recurso.')
        return redirect('dashboard:redirect')
    if config.get('form'):
        messages.info(request, 'Este recurso debe editarse desde el administrador avanzado.')
        return redirect('dashboard:admin_resource', resource=resource)
    instance = get_object_or_404(config['model'], pk=pk)
    form_class = build_admin_model_form(config['model'], config['fields'])
    form = style_admin_form(form_class(request.POST or None, request.FILES or None, instance=instance))
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f"Se actualizó correctamente el {config['singular']}.")
        return redirect('dashboard:admin_resource', resource=resource)
    return render(request, 'dashboard/admin_resource_form.html', {'resource': resource, 'config': config, 'form': form, 'is_edit': True, 'object': instance})


@login_required
@require_POST
def admin_resource_delete(request, resource, pk):
    config = ADMIN_RESOURCES.get(resource)
    if not config:
        messages.error(request, 'El recurso solicitado no existe.')
        return redirect('dashboard:admin')
    if not can_manage_resource(request.user, resource):
        messages.error(request, 'No tienes permiso para eliminar este recurso.')
        return redirect('dashboard:redirect')

    instance = get_object_or_404(config['model'], pk=pk)
    if isinstance(instance, CustomUser) and instance == request.user:
        messages.error(request, 'No puedes eliminar tu propia cuenta de administrador desde aquí.')
        return redirect('dashboard:admin_resource', resource=resource)

    label = str(instance)
    try:
        if isinstance(instance, (TeacherProfile, StudentProfile, ParentProfile)):
            user = instance.user
            if user == request.user:
                messages.error(request, 'No puedes eliminar tu propia cuenta desde aquí.')
                return redirect('dashboard:admin_resource', resource=resource)
            user.delete()
        else:
            instance.delete()
    except ProtectedError:
        messages.error(request, f'No se puede eliminar {label} porque está relacionado con otros registros.')
    else:
        messages.success(request, f'Se eliminó correctamente {label}.')
    return redirect('dashboard:admin_resource', resource=resource)


@login_required
@require_POST
def teacher_permissions_update(request, pk):
    if not is_admin_user(request.user):
        messages.error(request, 'No tienes permiso para cambiar permisos de docentes.')
        return redirect('dashboard:redirect')

    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=pk)
    teacher.can_manage_lessons = request.POST.get('can_manage_lessons') == 'on'
    teacher.can_manage_activities = request.POST.get('can_manage_activities') == 'on'
    teacher.can_manage_readings = request.POST.get('can_manage_readings') == 'on'
    teacher.save(update_fields=['can_manage_lessons', 'can_manage_activities', 'can_manage_readings'])
    messages.success(request, f'Se actualizaron los permisos de {teacher.name}.')
    return redirect('dashboard:admin_resource', resource='profesores')


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_list(request):
    plans = LessonPlan.objects.select_related('teacher', 'subject', 'level')
    if not is_admin_user(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        if teacher is None:
            messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
            return redirect('dashboard:teacher')
        plans = plans.filter(teacher=teacher)
    return render(request, 'dashboard/lesson_plan_list.html', {'plans': plans, 'create_form': LessonPlanForm()})


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_create(request):
    form = LessonPlanForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        plan = form.save(commit=False)
        if is_admin_user(request.user):
            teacher = TeacherProfile.objects.first()
            if teacher is None:
                messages.error(request, 'Debe existir al menos un profesor para crear un plan de clase.')
                return redirect('dashboard:lesson_plans')
            plan.teacher = teacher
        else:
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher is None:
                messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
                return redirect('dashboard:teacher')
            plan.teacher = teacher
        plan.save()
        form.save_m2m()
        messages.success(request, 'Plan de clase creado correctamente.')
        return redirect('dashboard:lesson_plans')
    return render(request, 'dashboard/lesson_plan_form.html', {'form': form, 'is_edit': False})


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_update(request, pk):
    plan = get_object_or_404(LessonPlan.objects.select_related('teacher'), pk=pk)
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para editar este plan de clase.')
        return redirect('dashboard:lesson_plans')
    form = LessonPlanForm(request.POST or None, instance=plan)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Plan de clase actualizado correctamente.')
        return redirect('dashboard:lesson_plans')
    return render(request, 'dashboard/lesson_plan_form.html', {'form': form, 'is_edit': True, 'plan': plan})


@login_required
@user_passes_test(is_teacher)
def quick_student_create(request):
    credentials = None
    form = QuickStudentCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user, password = form.save()
        credentials = {'username': user.username, 'password': password}
        messages.success(request, 'Alumno creado correctamente. Entrega estos datos al estudiante o tutor.')
        form = QuickStudentCreationForm()
    return render(request, 'dashboard/quick_student_form.html', {'form': form, 'credentials': credentials})


@login_required
def student_report(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related('user', 'current_level', 'reading_level'), pk=pk)
    own_report = getattr(request.user, 'student_profile', None) == student
    if not (own_report or is_teacher_or_admin(request.user)):
        messages.error(request, 'No tienes permiso para ver este reporte.')
        return redirect('dashboard:redirect')
    progress_items = StudentProgress.objects.filter(student=student).select_related('activity', 'activity__level').order_by('-last_activity_date')[:10]
    difficulties = StudentDifficulty.objects.filter(student=student).order_by('-error_count', '-last_error_date')[:8]
    attempts_count = student.attempts.count()
    completed_count = student.progress_items.filter(completed=True).count()
    total_progress = student.progress_items.count()
    completion_percentage = round((completed_count / total_progress) * 100) if total_progress else 0
    return render(request, 'dashboard/student_report.html', {
        'student': student,
        'progress_items': progress_items,
        'difficulties': difficulties,
        'attempts_count': attempts_count,
        'completed_count': completed_count,
        'completion_percentage': completion_percentage,
    })


@login_required
def student_dashboard(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.error(request, 'Tu cuenta no tiene un perfil de estudiante asignado.')
        return redirect('accounts:profile')
    evaluate_achievements(student)
    recommended = get_recommended_activities(student)
    return render(request, 'dashboard/student_dashboard.html', {'student': student, 'recommended': recommended})


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    students = StudentProfile.objects.select_related('user', 'current_level').annotate(
        completed_activities=Count('progress_items', filter=Q(progress_items__completed=True), distinct=True),
        total_attempts=Count('attempts', distinct=True),
        detected_difficulties=Count('difficulties', distinct=True),
    ).order_by('name')
    summary = {
        'students': students.count(),
        'completed_activities': sum(student.completed_activities for student in students),
        'attempts': sum(student.total_attempts for student in students),
        'difficulties': sum(student.detected_difficulties for student in students),
    }
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    lesson_plans = LessonPlan.objects.filter(teacher=teacher_profile).select_related('subject', 'level')[:4] if teacher_profile else []
    return render(request, 'dashboard/teacher_dashboard.html', {
        'students': students,
        'summary': summary,
        'teacher_profile': teacher_profile,
        'lesson_plans': lesson_plans,
    })


@login_required
@user_passes_test(is_parent)
def parent_dashboard(request):
    parent = getattr(request.user, 'parent_profile', None)
    if parent is None:
        messages.error(request, 'Tu cuenta familiar no tiene un perfil asignado.')
        return redirect('accounts:profile')
    return render(request, 'dashboard/parent_dashboard.html', {'parent': parent})
