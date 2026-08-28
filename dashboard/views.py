from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from activities.models import Activity
from activities.services import get_recommended_activities
from core.models import AuditLog
from gamification.models import StudentAchievement
from gamification.services import evaluate_achievements
from games.models import Game, GameAttempt, GameAttemptAnswer
from learning.models import CurriculumCompetency, FasStep, Lesson, LessonPlan, LessonPlanAssignment, Level, MinedReference, MinedStrategy, ParentProfile, StudentProfile, Subject, Syllable, TeacherProfile, Word
from progress.models import StudentDifficulty, StudentProgress
from readings.models import Reading, ReadingComprehensionAnswer, ReadingProgress

from .forms import AdminUserCreationForm, AdminUserUpdateForm, LessonPlanForm, QuickStudentCreationForm, TeacherCreationForm, TeacherStudentModalForm, TeacherStudentUpdateForm, TeacherUpdateForm, build_admin_model_form, style_admin_form


TEACHER_IMPERSONATION_USER_KEY = 'teacher_impersonation_user_id'
TEACHER_IMPERSONATION_PROFILE_KEY = 'teacher_impersonation_profile_id'
TEACHER_IMPERSONATION_STUDENT_KEY = 'teacher_impersonation_student_id'


ADMIN_RESOURCES = {
    'usuarios': {'title': 'Usuarios y roles', 'singular': 'usuario', 'model': CustomUser, 'form': AdminUserCreationForm, 'update_form': AdminUserUpdateForm, 'fields': None},
    'profesores': {'title': 'Profesores', 'singular': 'profesor', 'model': TeacherProfile, 'create_form': TeacherCreationForm, 'update_form': TeacherUpdateForm, 'fields': ('first_name', 'last_name', 'email', 'name', 'students', 'bio', 'is_active', 'can_create_students', 'can_view_student_reports', 'can_create_lesson_plans', 'can_edit_lesson_plans', 'can_assign_lesson_plans', 'can_manage_lessons', 'can_manage_activities', 'can_manage_readings', 'can_manage_games')},
    'alumnos': {'title': 'Alumnos', 'singular': 'alumno', 'model': StudentProfile, 'create_form': QuickStudentCreationForm, 'fields': ('user', 'name', 'alias', 'birth_date', 'grade', 'school', 'modality', 'zone', 'reading_level', 'current_level', 'points', 'stars')},
    'padres': {'title': 'Padres o tutores', 'singular': 'tutor', 'model': ParentProfile, 'fields': ('user', 'name', 'students')},
    'niveles': {'title': 'Niveles', 'singular': 'nivel', 'model': Level, 'fields': ('number', 'name', 'description', 'order', 'is_active')},
    'materias': {'title': 'Materias', 'singular': 'materia', 'model': Subject, 'fields': ('name', 'description', 'is_active')},
    'estrategias': {'title': 'Estrategias MINED', 'singular': 'estrategia', 'model': MinedStrategy, 'fields': ('name', 'description', 'focus', 'is_active')},
    'competencias': {'title': 'Competencias curriculares', 'singular': 'competencia', 'model': CurriculumCompetency, 'fields': ('pedagogical_unit', 'grade', 'subject', 'strategy', 'title', 'competency', 'achievement_indicator', 'dyslexia_adaptation', 'is_active')},
    'metodo-fas': {'title': 'Método FAS', 'singular': 'paso FAS', 'model': FasStep, 'fields': ('stage', 'title', 'description', 'grade', 'order', 'is_active')},
    'referencias-mined': {'title': 'Biblioteca MINED', 'singular': 'referencia', 'model': MinedReference, 'fields': ('title', 'resource_type', 'grade', 'subject', 'official_url', 'app_usage', 'is_active')},
    'clases': {'title': 'Clases', 'singular': 'clase', 'model': Lesson, 'fields': ('level', 'title', 'description', 'stage', 'order', 'is_active')},
    'actividades': {'title': 'Actividades', 'singular': 'actividad', 'model': Activity, 'fields': ('subject', 'competency', 'grade', 'level', 'title', 'description', 'instructions', 'activity_type', 'difficulty', 'points', 'stars', 'is_active')},
    'lecturas': {'title': 'Lecturas', 'singular': 'lectura', 'model': Reading, 'fields': ('subject', 'competency', 'grade', 'title', 'description', 'content', 'image', 'level', 'difficulty', 'estimated_time', 'audio_optional', 'is_active')},
    'juegos': {'title': 'Juegos', 'singular': 'juego', 'model': Game, 'fields': ('subject', 'competency', 'grade', 'name', 'slug', 'description', 'skill', 'game_type', 'level', 'icon', 'is_active')},
    'palabras': {'title': 'Palabras', 'singular': 'palabra', 'model': Word, 'fields': ('text', 'image', 'level', 'syllables')},
    'silabas': {'title': 'Sílabas', 'singular': 'sílaba', 'model': Syllable, 'fields': ('text', 'level')},
}


def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'


def is_admin_user(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_staff or user.is_superuser)


def is_report_admin_user(user):
    return user.is_authenticated and (user.role == 'ADMIN' or user.is_superuser)


def is_parent(user):
    return user.is_authenticated and user.role == 'PARENT'


def is_teacher_or_admin(user):
    return user.is_authenticated and (user.role in ('TEACHER', 'ADMIN') or user.is_staff or user.is_superuser)


def can_manage_resource(user, resource):
    if is_admin_user(user):
        return True
    teacher = getattr(user, 'teacher_profile', None)
    if not user.is_authenticated or user.role != 'TEACHER' or teacher is None or not teacher.is_active:
        return False
    permission_map = {
        'planes': teacher.can_create_lesson_plans or teacher.can_edit_lesson_plans or teacher.can_assign_lesson_plans,
        'actividades': teacher.can_manage_activities,
        'lecturas': teacher.can_manage_readings,
        'juegos': teacher.can_manage_games,
    }
    return permission_map.get(resource, False)


def teacher_has_permission(user, permission):
    if is_admin_user(user):
        return True
    teacher = getattr(user, 'teacher_profile', None)
    return user.is_authenticated and user.role == 'TEACHER' and teacher is not None and teacher.is_active and getattr(teacher, permission, False)


def teacher_can_access_student(user, student):
    teacher = getattr(user, 'teacher_profile', None)
    return bool(
        user.is_authenticated
        and user.role == 'TEACHER'
        and teacher is not None
        and teacher.is_active
        and teacher.students.filter(pk=student.pk).exists()
    )


def parent_can_access_student(user, student):
    parent = getattr(user, 'parent_profile', None)
    return bool(
        user.is_authenticated
        and user.role == 'PARENT'
        and parent is not None
        and parent.students.filter(pk=student.pk).exists()
    )


def user_can_view_student_report(user, student):
    own_report = getattr(user, 'student_profile', None) == student
    teacher_report = teacher_has_permission(user, 'can_view_student_reports') and teacher_can_access_student(user, student)
    return own_report or is_report_admin_user(user) or teacher_report or parent_can_access_student(user, student)


def user_can_manage_student_visual_key(user, student):
    return is_report_admin_user(user) or teacher_can_access_student(user, student)


def require_teacher_permission(request, permission, message):
    if teacher_has_permission(request.user, permission):
        return None
    messages.error(request, message)
    return redirect('dashboard:teacher')


def require_any_teacher_permission(request, permissions, message):
    if is_admin_user(request.user) or any(teacher_has_permission(request.user, permission) for permission in permissions):
        return None
    messages.error(request, message)
    return redirect('dashboard:teacher')


def write_audit(request, action, instance, metadata=None):
    AuditLog.objects.create(
        actor=request.user if request.user.is_authenticated else None,
        action=action,
        model_name=instance.__class__.__name__,
        object_id=str(getattr(instance, 'pk', '') or ''),
        object_repr=str(instance),
        metadata=metadata or {},
    )


def user_has_academic_history(user):
    student = getattr(user, 'student_profile', None)
    if student and (
        student.attempts.exists()
        or student.progress_items.exists()
        or student.difficulties.exists()
        or student.lesson_plan_assignments.exists()
    ):
        return True
    teacher = getattr(user, 'teacher_profile', None)
    return bool(teacher and teacher.lesson_plans.exists())


def resource_has_history(instance):
    if isinstance(instance, TeacherProfile):
        return instance.lesson_plans.exists()
    if isinstance(instance, StudentProfile):
        return (
            instance.attempts.exists()
            or instance.progress_items.exists()
            or instance.difficulties.exists()
            or instance.lesson_plan_assignments.exists()
        )
    if isinstance(instance, LessonPlan):
        return instance.assignments.exists()
    if isinstance(instance, Activity):
        return instance.attempts.exists() or instance.progress_items.exists() or instance.lesson_plans.exists()
    if isinstance(instance, Reading):
        return instance.student_progress.exists() or instance.student_answers.exists() or instance.lesson_plans.exists()
    if isinstance(instance, Game):
        return instance.attempts.exists() or instance.lesson_plans.exists()
    if isinstance(instance, (Reading, Game)):
        return instance.lesson_plans.exists()
    return False


def deactivate_resource(instance):
    if hasattr(instance, 'status') and isinstance(instance, LessonPlan):
        instance.status = LessonPlan.Status.ARCHIVED
        instance.is_active = False
        instance.save(update_fields=['status', 'is_active'])
    elif hasattr(instance, 'is_active'):
        instance.is_active = False
        instance.save(update_fields=['is_active'])


def is_teacher_resource_request(request):
    return request.resolver_match and request.resolver_match.url_name in {
        'teacher_resource',
        'teacher_resource_create',
        'teacher_resource_update',
        'teacher_resource_delete',
    }


def resource_redirect_name(request):
    return 'dashboard:teacher_resource' if is_teacher_resource_request(request) else 'dashboard:admin_resource'


def resource_create_route(request):
    return 'dashboard:teacher_resource_create' if is_teacher_resource_request(request) else 'dashboard:admin_resource_create'


def resource_update_route(request):
    return 'dashboard:teacher_resource_update' if is_teacher_resource_request(request) else 'dashboard:admin_resource_update'


def resource_delete_route(request):
    return 'dashboard:teacher_resource_delete' if is_teacher_resource_request(request) else 'dashboard:admin_resource_delete'


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
        'strategies': MinedStrategy.objects.count(),
        'competencies': CurriculumCompetency.objects.count(),
        'fas_steps': FasStep.objects.count(),
        'mined_references': MinedReference.objects.count(),
        'words': Word.objects.count(),
        'syllables': Syllable.objects.count(),
        'covered_competencies': CurriculumCompetency.objects.filter(Q(activities__isnull=False) | Q(readings__isnull=False) | Q(games__isnull=False)).distinct().count(),
    }
    recent_students = StudentProfile.objects.select_related('user', 'current_level').order_by('-created_at')[:5]
    recent_plans = LessonPlan.objects.select_related('teacher', 'subject', 'level').order_by('-created_at')[:5]
    return render(request, 'dashboard/admin_dashboard.html', {'stats': stats, 'recent_students': recent_students, 'recent_plans': recent_plans, 'resources': ADMIN_RESOURCES})


@login_required
def admin_resource_landing(request, resource):
    teacher_resource_page = is_teacher_resource_request(request)
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
    objects = list(objects.order_by('-pk')[:20])
    form_class = config.get('create_form') or config.get('form') or build_admin_model_form(config['model'], config['fields'])
    create_form = style_admin_form(form_class())
    edit_rows = []
    if config.get('update_form') or not config.get('form'):
        edit_form_class = config.get('update_form') or build_admin_model_form(config['model'], config['fields'])
        edit_rows = [
            {'object': item, 'form': style_admin_form(edit_form_class(instance=item))}
            for item in objects
        ]
    return render(request, 'dashboard/admin_resource_landing.html', {
        'resource': resource,
        'config': config,
        'objects': objects,
        'edit_rows': edit_rows,
        'create_form': create_form,
        'teacher_resource_page': teacher_resource_page,
        'resource_create_route': resource_create_route(request),
        'resource_update_route': resource_update_route(request),
        'resource_delete_route': resource_delete_route(request),
    })


@login_required
def admin_resource_create(request, resource):
    redirect_name = resource_redirect_name(request)
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
        instance = form.save()
        credentials = getattr(form, 'created_credentials', None)
        audit_instance = instance[0] if isinstance(instance, tuple) else instance
        write_audit(request, 'create', audit_instance, {'resource': resource})
        messages.success(request, f"Se agregó correctamente el {config['singular']}.")
        if request.POST.get('_from_modal'):
            if credentials:
                messages.success(request, f"Credenciales creadas - Usuario: {credentials['username']} / Contraseña: {credentials['password']}")
            return redirect(redirect_name, resource=resource)
        if credentials is None:
            return redirect(redirect_name, resource=resource)
        form = form_class()
    return render(request, 'dashboard/admin_resource_form.html', {'resource': resource, 'config': config, 'form': form, 'is_edit': False, 'credentials': credentials, 'teacher_resource_page': is_teacher_resource_request(request), 'resource_list_route': redirect_name})


@login_required
def admin_resource_update(request, resource, pk):
    redirect_name = resource_redirect_name(request)
    config = ADMIN_RESOURCES.get(resource)
    if not config:
        messages.error(request, 'El recurso solicitado no existe.')
        return redirect('dashboard:admin')
    if not can_manage_resource(request.user, resource):
        messages.error(request, 'No tienes permiso para editar este recurso.')
        return redirect('dashboard:redirect')
    if config.get('form') and not config.get('update_form'):
        messages.info(request, 'Este recurso debe editarse desde el administrador avanzado.')
        return redirect(redirect_name, resource=resource)
    instance = get_object_or_404(config['model'], pk=pk)
    if isinstance(instance, CustomUser) and instance.is_superuser:
        messages.error(request, 'El superusuario no se edita desde esta pantalla.')
        return redirect(redirect_name, resource=resource)
    form_class = config.get('update_form') or build_admin_model_form(config['model'], config['fields'])
    form = style_admin_form(form_class(request.POST or None, request.FILES or None, instance=instance))
    if request.method == 'POST' and form.is_valid():
        instance = form.save()
        write_audit(request, 'update', instance, {'resource': resource})
        messages.success(request, f"Se actualizó correctamente el {config['singular']}.")
        return redirect(redirect_name, resource=resource)
    return render(request, 'dashboard/admin_resource_form.html', {'resource': resource, 'config': config, 'form': form, 'is_edit': True, 'object': instance, 'teacher_resource_page': is_teacher_resource_request(request), 'resource_list_route': redirect_name})


@login_required
@require_POST
def admin_resource_delete(request, resource, pk):
    redirect_name = resource_redirect_name(request)
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
        return redirect(redirect_name, resource=resource)

    label = str(instance)
    action_message = f'Se eliminó correctamente {label}.'
    try:
        if isinstance(instance, CustomUser):
            teacher = getattr(instance, 'teacher_profile', None)
            if user_has_academic_history(instance):
                instance.is_active = False
                instance.save(update_fields=['is_active'])
                if teacher and teacher.is_active:
                    teacher.is_active = False
                    teacher.save(update_fields=['is_active'])
                write_audit(request, 'deactivate_with_history', instance, {'resource': resource})
                action_message = f'Se desactivó correctamente la cuenta de {label}. Su historial se conservó.'
            else:
                write_audit(request, 'delete', instance, {'resource': resource})
                if teacher:
                    teacher.delete()
                instance.delete()
        elif isinstance(instance, (StudentProfile, ParentProfile)):
            user = instance.user
            if user == request.user:
                messages.error(request, 'No puedes eliminar tu propia cuenta desde aquí.')
                return redirect(redirect_name, resource=resource)
            if resource_has_history(instance):
                user.is_active = False
                user.save(update_fields=['is_active'])
                write_audit(request, 'deactivate_with_history', instance, {'resource': resource, 'user_id': user.pk})
                action_message = f'Se desactivó correctamente {label}. Su historial académico se conservó.'
            else:
                write_audit(request, 'delete', instance, {'resource': resource, 'user_id': user.pk})
                user.delete()
        elif isinstance(instance, TeacherProfile):
            user = instance.user
            instance.is_active = False
            instance.save(update_fields=['is_active'])
            if user and user != request.user:
                user.is_active = False
                user.save(update_fields=['is_active'])
            write_audit(request, 'deactivate_teacher', instance, {'resource': resource, 'preserved_plans': instance.lesson_plans.count()})
            action_message = f'Se desactivó correctamente el docente {label}. Sus planes y reportes se conservaron.'
        elif resource_has_history(instance):
            deactivate_resource(instance)
            write_audit(request, 'archive_with_history', instance, {'resource': resource})
            action_message = f'Se archivó correctamente {label}. Su historial se conservó.'
        else:
            write_audit(request, 'delete', instance, {'resource': resource})
            instance.delete()
    except ProtectedError:
        messages.error(request, f'No se puede eliminar {label} porque está relacionado con otros registros.')
    else:
        messages.success(request, action_message)
    return redirect(redirect_name, resource=resource)


@login_required
@require_POST
def teacher_permissions_update(request, pk):
    if not is_admin_user(request.user):
        messages.error(request, 'No tienes permiso para cambiar permisos de docentes.')
        return redirect('dashboard:redirect')

    teacher = get_object_or_404(TeacherProfile.objects.select_related('user'), pk=pk)
    teacher.can_create_students = request.POST.get('can_create_students') == 'on'
    teacher.can_view_student_reports = request.POST.get('can_view_student_reports') == 'on'
    teacher.can_create_lesson_plans = request.POST.get('can_create_lesson_plans') == 'on'
    teacher.can_edit_lesson_plans = request.POST.get('can_edit_lesson_plans') == 'on'
    teacher.can_assign_lesson_plans = request.POST.get('can_assign_lesson_plans') == 'on'
    teacher.can_manage_lessons = request.POST.get('can_manage_lessons') == 'on'
    teacher.can_manage_activities = request.POST.get('can_manage_activities') == 'on'
    teacher.can_manage_readings = request.POST.get('can_manage_readings') == 'on'
    teacher.can_manage_games = request.POST.get('can_manage_games') == 'on'
    teacher.save(update_fields=[
        'can_create_students', 'can_view_student_reports',
        'can_create_lesson_plans', 'can_edit_lesson_plans', 'can_assign_lesson_plans',
        'can_manage_lessons', 'can_manage_activities', 'can_manage_readings', 'can_manage_games',
    ])
    messages.success(request, f'Se actualizaron los permisos de {teacher.name}.')
    return redirect('dashboard:admin_resource', resource='profesores')


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_list(request):
    permission_response = require_any_teacher_permission(
        request,
        ('can_create_lesson_plans', 'can_edit_lesson_plans', 'can_assign_lesson_plans'),
        'No tienes permiso para ver planes de clase.',
    )
    if permission_response:
        return permission_response
    plans = LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings', 'games')
    teacher = None
    if not is_admin_user(request.user):
        teacher = getattr(request.user, 'teacher_profile', None)
        if teacher is None:
            messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
            return redirect('dashboard:teacher')
        plans = plans.filter(teacher=teacher)
    return render(request, 'dashboard/lesson_plan_list.html', {'plans': plans, 'create_form': LessonPlanForm(teacher=teacher)})


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_create(request):
    permission_response = require_teacher_permission(request, 'can_create_lesson_plans', 'No tienes permiso para crear planes de clase.')
    if permission_response:
        return permission_response
    teacher = None if is_admin_user(request.user) else getattr(request.user, 'teacher_profile', None)
    form = LessonPlanForm(request.POST or None, teacher=teacher)
    if request.method == 'POST' and form.is_valid():
        plan = form.save(commit=False)
        if is_admin_user(request.user):
            teacher = TeacherProfile.objects.first()
            if teacher is None:
                messages.error(request, 'Debe existir al menos un profesor para crear un plan de clase.')
                return redirect('dashboard:lesson_plans')
            plan.teacher = teacher
        else:
            if teacher is None:
                messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
                return redirect('dashboard:teacher')
            plan.teacher = teacher
        plan.save()
        form.save_m2m()
        form.save_assignments(plan)
        write_audit(request, 'create_lesson_plan', plan)
        messages.success(request, 'Plan de clase creado correctamente.')
        return redirect('dashboard:lesson_plans')
    if request.method == 'POST':
        plans = LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings', 'games')
        if not is_admin_user(request.user):
            teacher = getattr(request.user, 'teacher_profile', None)
            if teacher is None:
                messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
                return redirect('dashboard:teacher')
            plans = plans.filter(teacher=teacher)
        return render(request, 'dashboard/lesson_plan_list.html', {'plans': plans, 'create_form': form, 'open_create_modal': True})
    return render(request, 'dashboard/lesson_plan_form.html', {'form': form, 'is_edit': False})


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_update(request, pk):
    permission_response = require_teacher_permission(request, 'can_edit_lesson_plans', 'No tienes permiso para editar planes de clase.')
    if permission_response:
        return permission_response
    plan = get_object_or_404(LessonPlan.objects.select_related('teacher'), pk=pk)
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para editar este plan de clase.')
        return redirect('dashboard:lesson_plans')
    form = LessonPlanForm(request.POST or None, instance=plan, teacher=None if is_admin_user(request.user) else teacher)
    if request.method == 'POST' and form.is_valid():
        plan = form.save()
        form.save_assignments(plan)
        write_audit(request, 'update_lesson_plan', plan)
        messages.success(request, 'Plan de clase actualizado correctamente.')
        return redirect('dashboard:lesson_plans')
    return render(request, 'dashboard/lesson_plan_form.html', {'form': form, 'is_edit': True, 'plan': plan})


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_implementation(request, pk):
    permission_response = require_teacher_permission(request, 'can_assign_lesson_plans', 'No tienes permiso para asignar o implementar planes de clase.')
    if permission_response:
        return permission_response
    plan = get_object_or_404(
        LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings', 'games'),
        pk=pk,
    )
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para implementar este plan de clase.')
        return redirect('dashboard:lesson_plans')

    activity_ids = plan.activities.values_list('id', flat=True)
    reading_ids = plan.readings.values_list('id', flat=True)
    game_ids = plan.games.values_list('id', flat=True)
    suggested_activities = Activity.objects.filter(
        is_active=True,
        level=plan.level,
        subject=plan.subject,
        grade=plan.grade,
    ).exclude(id__in=activity_ids).select_related('subject', 'level')[:6]
    suggested_readings = Reading.objects.filter(
        is_active=True,
        level=plan.level,
        subject=plan.subject,
        grade=plan.grade,
    ).exclude(id__in=reading_ids).select_related('subject', 'level')[:6]
    suggested_games = Game.objects.filter(
        is_active=True,
        level=plan.level,
        subject=plan.subject,
        grade__in=('', plan.grade),
    ).exclude(id__in=game_ids).select_related('subject', 'level')[:6]

    return render(request, 'dashboard/lesson_plan_implementation.html', {
        'plan': plan,
        'assigned_students': plan.assignments.select_related('student', 'student__current_level'),
        'suggested_activities': suggested_activities,
        'suggested_readings': suggested_readings,
        'suggested_games': suggested_games,
    })


@login_required
@user_passes_test(is_teacher_or_admin)
def lesson_plan_report(request, pk):
    permission_response = require_any_teacher_permission(
        request,
        ('can_assign_lesson_plans', 'can_view_student_reports'),
        'No tienes permiso para ver reportes de planes de clase.',
    )
    if permission_response:
        return permission_response
    plan = get_object_or_404(
        LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings', 'games'),
        pk=pk,
    )
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para ver el reporte de este plan de clase.')
        return redirect('dashboard:lesson_plans')

    assignments = list(
        plan.assignments.select_related('student', 'student__current_level', 'student__reading_level').order_by('student__name')
    )
    total_assignments = len(assignments)
    completed_count = sum(1 for assignment in assignments if assignment.status == LessonPlanAssignment.Status.COMPLETED)
    in_progress_count = sum(1 for assignment in assignments if assignment.status == LessonPlanAssignment.Status.IN_PROGRESS)
    assigned_count = sum(1 for assignment in assignments if assignment.status == LessonPlanAssignment.Status.ASSIGNED)
    completion_percentage = round((completed_count / total_assignments) * 100) if total_assignments else 0
    student_ids = [assignment.student_id for assignment in assignments]
    difficulties = StudentDifficulty.objects.filter(student_id__in=student_ids).select_related('student').order_by('-error_count', '-last_error_date')[:8]

    reinforcement_recommendations = []
    if assigned_count:
        reinforcement_recommendations.append('Iniciar con lectura modelada y una instrucción corta para estudiantes aún asignados.')
    if in_progress_count:
        reinforcement_recommendations.append('Reforzar con práctica silábica, apoyo visual y relectura acompañada para quienes están en progreso.')
    if difficulties:
        reinforcement_recommendations.append('Usar juegos y lecturas del mismo nivel para trabajar los errores frecuentes detectados.')
    if total_assignments and completion_percentage < 70:
        reinforcement_recommendations.append('Dividir el plan en pasos más breves antes de marcarlo como completado.')
    if not reinforcement_recommendations:
        reinforcement_recommendations.append('Mantener actividades multisensoriales y registrar notas breves después de cada sesión.')

    return render(request, 'dashboard/lesson_plan_report.html', {
        'plan': plan,
        'assignments': assignments,
        'assigned_count': assigned_count,
        'in_progress_count': in_progress_count,
        'completed_count': completed_count,
        'completion_percentage': completion_percentage,
        'difficulties': difficulties,
        'reinforcement_recommendations': reinforcement_recommendations,
        'status_choices': LessonPlanAssignment.Status.choices,
        'can_update_assignments': is_admin_user(request.user) or teacher_has_permission(request.user, 'can_assign_lesson_plans'),
    })


@login_required
@user_passes_test(is_teacher_or_admin)
@require_POST
def lesson_plan_assignment_update(request, pk, assignment_pk):
    permission_response = require_teacher_permission(request, 'can_assign_lesson_plans', 'No tienes permiso para actualizar el seguimiento del plan.')
    if permission_response:
        return permission_response
    assignment = get_object_or_404(
        LessonPlanAssignment.objects.select_related('plan', 'plan__teacher'),
        pk=assignment_pk,
        plan_id=pk,
    )
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and assignment.plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para actualizar este seguimiento.')
        return redirect('dashboard:lesson_plans')

    status = request.POST.get('status')
    valid_statuses = {choice[0] for choice in LessonPlanAssignment.Status.choices}
    if status not in valid_statuses:
        messages.error(request, 'Selecciona un estado válido para el seguimiento.')
        return redirect('dashboard:lesson_plan_report', pk=pk)

    assignment.status = status
    assignment.teacher_notes = request.POST.get('teacher_notes', '').strip()
    assignment.completed_at = timezone.now() if status == LessonPlanAssignment.Status.COMPLETED else None
    assignment.save(update_fields=['status', 'teacher_notes', 'completed_at'])
    write_audit(request, 'update_lesson_plan_assignment', assignment, {'status': status})
    messages.success(request, 'Seguimiento del estudiante actualizado.')
    return redirect('dashboard:lesson_plan_report', pk=pk)


@login_required
@user_passes_test(is_teacher)
def quick_student_create(request):
    permission_response = require_teacher_permission(request, 'can_create_students', 'No tienes permiso para crear estudiantes.')
    if permission_response:
        return permission_response
    credentials = None
    teacher = getattr(request.user, 'teacher_profile', None)
    if teacher is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('dashboard:teacher')
    form = QuickStudentCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user, password = form.save(teacher=teacher)
        credentials = {'username': user.username, 'password': password}
        messages.success(request, 'Alumno creado correctamente. Entrega estos datos al estudiante o tutor.')
        form = QuickStudentCreationForm()
    return render(request, 'dashboard/quick_student_form.html', {'form': form, 'credentials': credentials})


@login_required
def student_report(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related('user', 'current_level', 'reading_level'), pk=pk)
    if not user_can_view_student_report(request.user, student):
        messages.error(request, 'No tienes permiso para ver este reporte.')
        return redirect('dashboard:redirect')
    progress_items = StudentProgress.objects.filter(student=student).select_related('activity', 'activity__level').order_by('-last_activity_date')[:10]
    difficulties = StudentDifficulty.objects.filter(student=student).order_by('-error_count', '-last_error_date')[:8]
    attempts_count = student.attempts.count()
    game_attempts = GameAttempt.objects.filter(student=student).select_related('game', 'game__level', 'game__subject').order_by('-started_at')[:8]
    completed_count = student.progress_items.filter(completed=True).count()
    total_progress = student.progress_items.count()
    completion_percentage = round((completed_count / total_progress) * 100) if total_progress else 0
    reading_progress = ReadingProgress.objects.filter(student=student).select_related('reading', 'reading__level', 'reading__subject').order_by('-started_at')[:10]
    reading_rows = []
    for item in reading_progress:
        total_questions = item.reading.questions.count()
        correct_answers = ReadingComprehensionAnswer.objects.filter(student=student, reading=item.reading, is_correct=True).count()
        answered_questions = ReadingComprehensionAnswer.objects.filter(student=student, reading=item.reading).count()
        reading_rows.append({
            'progress': item,
            'reading': item.reading,
            'total_questions': total_questions,
            'answered_questions': answered_questions,
            'correct_answers': correct_answers,
        })
    quiz_subject_progress = []
    answer_rows = GameAttemptAnswer.objects.filter(attempt__student=student).values('subject').annotate(
        total=Count('id'),
        correct=Count('id', filter=Q(is_correct=True)),
    ).order_by('subject')
    for row in answer_rows:
        total = row['total'] or 0
        correct = row['correct'] or 0
        quiz_subject_progress.append({
            'subject': row['subject'] or 'Sin materia',
            'total': total,
            'correct': correct,
            'percentage': round((correct / total) * 100) if total else 0,
        })
    achievements = StudentAchievement.objects.filter(student=student).select_related('achievement').order_by('-earned_at')[:6]
    return render(request, 'dashboard/student_report.html', {
        'student': student,
        'progress_items': progress_items,
        'difficulties': difficulties,
        'attempts_count': attempts_count,
        'game_attempts': game_attempts,
        'game_attempts_count': student.game_attempts.count(),
        'reading_rows': reading_rows,
        'readings_started_count': student.reading_progress.count(),
        'readings_completed_count': student.reading_progress.filter(completed=True).count(),
        'completed_count': completed_count,
        'completion_percentage': completion_percentage,
        'quiz_subject_progress': quiz_subject_progress,
        'achievements': achievements,
    })


@login_required
def student_dashboard(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.error(request, 'Tu cuenta no tiene un perfil de estudiante asignado.')
        return redirect('accounts:profile')
    evaluate_achievements(student)
    recommended = get_recommended_activities(student)
    visible_plan_statuses = (LessonPlan.Status.ACTIVE, LessonPlan.Status.IN_PROGRESS)
    assigned_plans = LessonPlanAssignment.objects.filter(
        student=student,
        plan__is_active=True,
        plan__status__in=visible_plan_statuses,
    ).select_related('plan', 'plan__subject', 'plan__level').prefetch_related('plan__activities', 'plan__readings', 'plan__games')[:3]
    today_plan = assigned_plans[0] if assigned_plans else None
    return render(request, 'dashboard/student_dashboard.html', {'student': student, 'recommended': recommended, 'assigned_plans': assigned_plans, 'today_plan': today_plan})


@login_required
def student_lesson_plan(request, pk):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.error(request, 'Tu cuenta no tiene un perfil de estudiante asignado.')
        return redirect('accounts:profile')
    assignment = get_object_or_404(
        LessonPlanAssignment.objects.select_related('plan', 'plan__subject', 'plan__level').prefetch_related('plan__activities', 'plan__readings', 'plan__games'),
        plan_id=pk,
        student=student,
        plan__is_active=True,
        plan__status__in=(LessonPlan.Status.ACTIVE, LessonPlan.Status.IN_PROGRESS),
    )
    plan = assignment.plan
    return render(request, 'dashboard/student_lesson_plan.html', {'assignment': assignment, 'plan': plan})


@login_required
@user_passes_test(is_teacher)
def teacher_students(request):
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('accounts:profile')
    students = get_teacher_students_for_page(teacher_profile)
    return render(request, 'dashboard/teacher_students.html', {'teacher_profile': teacher_profile, 'students': students})


def get_teacher_students_for_page(teacher_profile, edit_form=None, open_edit_student=None):
    students = list(teacher_profile.students.select_related('user', 'current_level').prefetch_related('parents').annotate(
        completed_activities=Count('progress_items', filter=Q(progress_items__completed=True), distinct=True),
        total_attempts=Count('attempts', distinct=True),
        detected_difficulties=Count('difficulties', distinct=True),
    ).order_by('name'))
    for student in students:
        student.edit_form = edit_form if edit_form is not None and student.pk == open_edit_student else TeacherStudentModalForm(instance=student)
        student.open_edit_modal = student.pk == open_edit_student
    return students


@login_required
@user_passes_test(is_teacher)
@require_POST
def teacher_student_login(request, pk):
    if request.session.get(TEACHER_IMPERSONATION_USER_KEY):
        messages.error(request, 'Ya estás viendo una cuenta de estudiante.')
        return redirect('dashboard:student')
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('accounts:profile')
    student = get_object_or_404(teacher_profile.students.select_related('user'), pk=pk)
    if not student.user.is_active:
        messages.error(request, 'Este estudiante no tiene una cuenta activa.')
        return redirect('dashboard:teacher_students')
    login(request, student.user, backend='django.contrib.auth.backends.ModelBackend')
    request.session[TEACHER_IMPERSONATION_USER_KEY] = teacher_profile.user_id
    request.session[TEACHER_IMPERSONATION_PROFILE_KEY] = teacher_profile.id
    request.session[TEACHER_IMPERSONATION_STUDENT_KEY] = student.id
    messages.success(request, f'Entraste al modo estudiante de {student.display_name()}.')
    return redirect('dashboard:student')


@login_required
@require_POST
def teacher_student_return(request):
    teacher_user_id = request.session.get(TEACHER_IMPERSONATION_USER_KEY)
    teacher_profile_id = request.session.get(TEACHER_IMPERSONATION_PROFILE_KEY)
    student_id = request.session.get(TEACHER_IMPERSONATION_STUDENT_KEY)
    current_student = getattr(request.user, 'student_profile', None)
    teacher_user = CustomUser.objects.filter(pk=teacher_user_id, role=CustomUser.Role.TEACHER, is_active=True).first()
    teacher_profile = TeacherProfile.objects.filter(pk=teacher_profile_id, user=teacher_user, is_active=True).first()
    valid_session = bool(
        current_student
        and teacher_user
        and teacher_profile
        and current_student.pk == student_id
        and teacher_profile.students.filter(pk=current_student.pk).exists()
    )
    if not valid_session:
        for key in (TEACHER_IMPERSONATION_USER_KEY, TEACHER_IMPERSONATION_PROFILE_KEY, TEACHER_IMPERSONATION_STUDENT_KEY):
            request.session.pop(key, None)
        logout(request)
        messages.error(request, 'Se cerró el modo temporal por seguridad.')
        return redirect('accounts:login')

    login(request, teacher_user, backend='django.contrib.auth.backends.ModelBackend')
    for key in (TEACHER_IMPERSONATION_USER_KEY, TEACHER_IMPERSONATION_PROFILE_KEY, TEACHER_IMPERSONATION_STUDENT_KEY):
        request.session.pop(key, None)
    messages.success(request, 'Volviste a tu cuenta docente.')
    return redirect('dashboard:teacher_students')


@login_required
@require_POST
def teacher_student_visual_key_regenerate(request, pk):
    student = get_object_or_404(StudentProfile.objects.select_related('user', 'current_level'), pk=pk)
    if not user_can_manage_student_visual_key(request.user, student):
        messages.error(request, 'No tienes permiso para crear dibujos secretos de este alumno.')
        return redirect('dashboard:redirect')
    visual_key = student.generate_visual_key()
    action = 'regeneró' if request.POST.get('had_visual_key') == '1' else 'creó'
    write_audit(request, f'{action}_student_visual_key', student)
    messages.success(request, 'Dibujos secretos listos. Guarda esta tarjeta en un lugar seguro.')
    return render(request, 'dashboard/student_visual_key_card.html', {
        'student': student,
        'visual_key': visual_key,
        'pin': request.POST.get('pin', ''),
        'back_url': 'dashboard:teacher_students' if request.user.role == 'TEACHER' else 'dashboard:redirect',
    })


@login_required
@user_passes_test(is_teacher)
def teacher_student_update(request, pk):
    permission_response = require_teacher_permission(request, 'can_create_students', 'No tienes permiso para editar estudiantes.')
    if permission_response:
        return permission_response
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('accounts:profile')
    student = get_object_or_404(teacher_profile.students.select_related('user'), pk=pk)
    if request.method != 'POST':
        return redirect('dashboard:teacher_students')
    form = TeacherStudentModalForm(request.POST, instance=student)
    if request.method == 'POST' and form.is_valid():
        form.save()
        write_audit(request, 'update_teacher_student', student, {'teacher_id': teacher_profile.pk})
        messages.success(request, 'Alumno actualizado correctamente.')
        return redirect('dashboard:teacher_students')
    students = get_teacher_students_for_page(teacher_profile, edit_form=form, open_edit_student=student.pk)
    return render(request, 'dashboard/teacher_students.html', {
        'teacher_profile': teacher_profile,
        'students': students,
        'open_edit_student': student.pk,
    })


@login_required
@user_passes_test(is_teacher)
@require_POST
def teacher_student_delete(request, pk):
    permission_response = require_teacher_permission(request, 'can_create_students', 'No tienes permiso para eliminar estudiantes.')
    if permission_response:
        return permission_response
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('accounts:profile')
    student = get_object_or_404(teacher_profile.students.select_related('user'), pk=pk)
    label = student.display_name()
    teacher_profile.students.remove(student)
    write_audit(request, 'unlink_teacher_student', student, {'teacher_id': teacher_profile.pk})
    messages.success(request, f'Se quitó {label} de tus alumnos. Su cuenta, progreso y demás información se conservaron.')
    return redirect('dashboard:teacher_students')


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    teacher_profile = getattr(request.user, 'teacher_profile', None)
    if teacher_profile is None:
        messages.error(request, 'Tu cuenta docente no tiene un perfil asignado.')
        return redirect('accounts:profile')
    students = teacher_profile.students.select_related('user', 'current_level').annotate(
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
    lesson_plan_queryset = LessonPlan.objects.filter(teacher=teacher_profile).select_related('subject', 'level').prefetch_related('activities', 'readings', 'games')
    summary['lesson_plans'] = lesson_plan_queryset.count()
    lesson_plans = lesson_plan_queryset[:5]
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
    students = parent.students.select_related('current_level', 'reading_level').annotate(
        completed_activities=Count('progress_items', filter=Q(progress_items__completed=True), distinct=True),
        total_attempts=Count('attempts', distinct=True),
        detected_difficulties=Count('difficulties', distinct=True),
    ).order_by('name')
    return render(request, 'dashboard/parent_dashboard.html', {'parent': parent, 'students': students})
