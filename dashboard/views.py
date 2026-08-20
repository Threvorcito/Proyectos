from django.contrib import messages
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
from gamification.services import evaluate_achievements
from games.models import Game
from learning.models import CurriculumCompetency, FasStep, Lesson, LessonPlan, LessonPlanAssignment, Level, MinedReference, MinedStrategy, ParentProfile, StudentProfile, Subject, Syllable, TeacherProfile, Word
from progress.models import StudentDifficulty, StudentProgress
from readings.models import Reading

from .forms import AdminUserCreationForm, AdminUserUpdateForm, LessonPlanForm, QuickStudentCreationForm, TeacherCreationForm, TeacherUpdateForm, build_admin_model_form, style_admin_form


ADMIN_RESOURCES = {
    'usuarios': {'title': 'Usuarios y roles', 'singular': 'usuario', 'model': CustomUser, 'form': AdminUserCreationForm, 'update_form': AdminUserUpdateForm, 'fields': None},
    'profesores': {'title': 'Profesores', 'singular': 'profesor', 'model': TeacherProfile, 'create_form': TeacherCreationForm, 'update_form': TeacherUpdateForm, 'fields': ('first_name', 'last_name', 'email', 'name', 'bio', 'is_active', 'can_create_students', 'can_view_student_reports', 'can_create_lesson_plans', 'can_edit_lesson_plans', 'can_assign_lesson_plans', 'can_manage_lessons', 'can_manage_activities', 'can_manage_readings', 'can_manage_games')},
    'alumnos': {'title': 'Alumnos', 'singular': 'alumno', 'model': StudentProfile, 'create_form': QuickStudentCreationForm, 'fields': ('user', 'name', 'alias', 'birth_date', 'grade', 'school', 'modality', 'zone', 'reading_level', 'current_level', 'points', 'stars')},
    'padres': {'title': 'Padres o tutores', 'singular': 'tutor', 'model': ParentProfile, 'fields': ('user', 'name')},
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
        'clases': teacher.can_manage_lessons,
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
        instance = form.save()
        credentials = getattr(form, 'created_credentials', None)
        audit_instance = instance[0] if isinstance(instance, tuple) else instance
        write_audit(request, 'create', audit_instance, {'resource': resource})
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
    if config.get('form') and not config.get('update_form'):
        messages.info(request, 'Este recurso debe editarse desde el administrador avanzado.')
        return redirect('dashboard:admin_resource', resource=resource)
    instance = get_object_or_404(config['model'], pk=pk)
    if isinstance(instance, CustomUser) and instance.is_superuser:
        messages.error(request, 'El superusuario no se edita desde esta pantalla.')
        return redirect('dashboard:admin_resource', resource=resource)
    form_class = config.get('update_form') or build_admin_model_form(config['model'], config['fields'])
    form = style_admin_form(form_class(request.POST or None, request.FILES or None, instance=instance))
    if request.method == 'POST' and form.is_valid():
        instance = form.save()
        write_audit(request, 'update', instance, {'resource': resource})
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
                return redirect('dashboard:admin_resource', resource=resource)
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
    return redirect('dashboard:admin_resource', resource=resource)


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
    plans = LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings')
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
    permission_response = require_teacher_permission(request, 'can_create_lesson_plans', 'No tienes permiso para crear planes de clase.')
    if permission_response:
        return permission_response
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
        form.save_assignments(plan)
        write_audit(request, 'create_lesson_plan', plan)
        messages.success(request, 'Plan de clase creado correctamente.')
        return redirect('dashboard:lesson_plans')
    if request.method == 'POST':
        plans = LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings')
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
    form = LessonPlanForm(request.POST or None, instance=plan)
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
        LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings'),
        pk=pk,
    )
    teacher = getattr(request.user, 'teacher_profile', None)
    if not is_admin_user(request.user) and plan.teacher != teacher:
        messages.error(request, 'No tienes permiso para implementar este plan de clase.')
        return redirect('dashboard:lesson_plans')

    activity_ids = plan.activities.values_list('id', flat=True)
    reading_ids = plan.readings.values_list('id', flat=True)
    suggested_activities = Activity.objects.filter(
        is_active=True,
        level=plan.level,
        grade=plan.grade,
    ).exclude(id__in=activity_ids).select_related('subject', 'level')[:6]
    suggested_readings = Reading.objects.filter(
        is_active=True,
        level=plan.level,
        grade=plan.grade,
    ).exclude(id__in=reading_ids).select_related('subject', 'level')[:6]
    suggested_games = Game.objects.filter(
        is_active=True,
        level=plan.level,
        grade=plan.grade,
    ).select_related('subject', 'level')[:6]

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
        LessonPlan.objects.select_related('teacher', 'subject', 'level').prefetch_related('activities', 'readings'),
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
    can_view_report = own_report or is_admin_user(request.user) or teacher_has_permission(request.user, 'can_view_student_reports')
    if not can_view_report:
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
    assigned_plans = LessonPlanAssignment.objects.filter(student=student).select_related('plan', 'plan__subject', 'plan__level').prefetch_related('plan__activities', 'plan__readings')[:3]
    today_plan = assigned_plans[0] if assigned_plans else None
    return render(request, 'dashboard/student_dashboard.html', {'student': student, 'recommended': recommended, 'assigned_plans': assigned_plans, 'today_plan': today_plan})


@login_required
def student_lesson_plan(request, pk):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.error(request, 'Tu cuenta no tiene un perfil de estudiante asignado.')
        return redirect('accounts:profile')
    assignment = get_object_or_404(
        LessonPlanAssignment.objects.select_related('plan', 'plan__subject', 'plan__level').prefetch_related('plan__activities', 'plan__readings'),
        plan_id=pk,
        student=student,
    )
    plan = assignment.plan
    suggested_games = Game.objects.filter(is_active=True, level=plan.level, grade=plan.grade).select_related('subject', 'level')[:4]
    return render(request, 'dashboard/student_lesson_plan.html', {'assignment': assignment, 'plan': plan, 'suggested_games': suggested_games})


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
    lesson_plan_queryset = LessonPlan.objects.filter(teacher=teacher_profile).select_related('subject', 'level').prefetch_related('activities', 'readings') if teacher_profile else LessonPlan.objects.none()
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
    return render(request, 'dashboard/parent_dashboard.html', {'parent': parent})
