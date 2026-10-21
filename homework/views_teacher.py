from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.views import RESOURCE_PAGE_SIZE, is_admin_user, write_audit
from learning.models import Subject

from readings.services import MAX_READ_MS, MIN_READ_MS, PRACTICE_READS

from .copy import FEEDBACK, INSTRUCTIONS
from .fas_content import lesson_for
from .fas_lessons import build_daily_class, letter_statuses
from .fas_sequence import GROUPS, VOWELS
from .forms import STEP_FORMS, AssignStudentsForm, SnepaOverrideForm, TaskForm
from .models import SnepaLevel, Task, TaskAssignment, TaskStep
from .permissions import can_manage_tasks, can_view_difficulty_data, can_view_task, difficulty_viewer
from .reports import assignment_detail, break_point_groups, dictation_sheet, task_rows
from .services import (
    TaskLocked,
    append_step,
    assign_students,
    delete_step,
    duplicate_task,
    ensure_editable,
    move_step,
    update_step,
)
from .views_student import _instruction_key, step_context

DENIED = 'No tienes permiso para gestionar tareas.'
LOCKED = 'Un alumno ya empezó esta tarea. Para cambiar los pasos, duplícala.'


def _deny(request):
    messages.error(request, DENIED)
    return redirect('dashboard:teacher')


def _task_or_404(request, pk, *, active_only=False):
    tasks = Task.objects.select_related('subject', 'teacher')
    if active_only:
        tasks = tasks.filter(is_active=True)
    task = get_object_or_404(tasks, pk=pk)
    if not can_view_task(request.user, task):
        raise Http404
    return task


@login_required
def task_list(request):
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    tasks = Task.objects.filter(is_active=True).select_related('subject', 'teacher').annotate(
        total=Count('assignments', distinct=True),
        completed=Count('assignments', filter=Q(assignments__status='completed'), distinct=True),
    )
    if not is_admin_user(request.user):
        tasks = tasks.filter(teacher=request.user.teacher_profile)
    search_term = request.GET.get('q', '').strip()
    if search_term:
        tasks = tasks.filter(title__icontains=search_term)
    page_obj = Paginator(tasks.order_by('-created_at', '-pk'), RESOURCE_PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, 'homework/teacher/task_list.html', {
        'tasks': page_obj,
        'page_obj': page_obj,
        'search_term': search_term,
        'can_manage': can_manage_tasks(request.user),
    })


@login_required
def task_create(request):
    if not can_manage_tasks(request.user):
        return _deny(request)
    teacher = request.user.teacher_profile
    form = TaskForm(request.POST or None, teacher=teacher)
    if request.method == 'POST' and form.is_valid():
        task = form.save(commit=False)
        task.teacher = teacher
        task.save()
        write_audit(request, 'create_task', task)
        messages.success(request, 'Tarea creada. Ahora puedes asignarla a tus alumnos.')
        return redirect('homework:task_detail', pk=task.pk)
    return render(request, 'homework/teacher/task_form.html', {'form': form, 'is_edit': False})


FAS_SUBJECT = 'Lengua y Literatura'


@login_required
def fas_sequence(request):
    if not can_manage_tasks(request.user):
        return _deny(request)
    statuses = letter_statuses(request.user.teacher_profile)
    groups = [
        (label, [
            {
                'letter': letter,
                'is_vowel': letter in VOWELS,
                'has_lesson': lesson_for(letter) is not None,
                'status': statuses.get(letter, ''),
            }
            for letter in letters
        ])
        for label, letters in GROUPS
    ]
    return render(request, 'homework/teacher/fas_sequence.html', {'groups': groups})


@login_required
@require_POST
def fas_class_create(request, letter):
    if not can_manage_tasks(request.user):
        return _deny(request)
    if lesson_for(letter) is None:
        raise Http404
    subject = Subject.objects.filter(name=FAS_SUBJECT).first()
    if subject is None:
        messages.error(request, f'No existe la materia «{FAS_SUBJECT}». Pide al administrador que la cree para usar la secuencia FAS.')
        return redirect('homework:fas_sequence')
    task = build_daily_class(request.user.teacher_profile, letter, subject)
    write_audit(request, 'create_fas_class', task, metadata={'letter': letter})
    messages.success(request, f'Clase de la «{letter}» creada. Revísala y asígnala a tus alumnos.')
    return redirect('homework:task_detail', pk=task.pk)

@login_required
def task_update(request, pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    locked = task.is_locked
    form = TaskForm(request.POST or None, instance=task, teacher=request.user.teacher_profile, locked=locked)
    if request.method == 'POST' and form.is_valid():
        form.save()
        write_audit(request, 'update_task', task)
        messages.success(request, 'Tarea actualizada.')
        return redirect('homework:task_detail', pk=task.pk)
    return render(request, 'homework/teacher/task_form.html', {'form': form, 'task': task, 'is_edit': True, 'locked': locked})


def _summary(step):
    payload = step.payload
    if step.step_type == TaskStep.StepType.DICTADO:
        return f'Letra «{payload["letter"]}»: {", ".join(payload["words"])}'
    return payload.get('question') or payload.get('text') or step.text or (payload.get('example_steps') or [''])[0]


@login_required
def task_detail(request, pk):
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    task = _task_or_404(request, pk)
    can_manage = can_manage_tasks(request.user)
    return render(request, 'homework/teacher/task_detail.html', {
        'task': task,
        'steps': [(step, _summary(step)) for step in task.steps.select_related('reading')],
        'step_types': [(slug, TaskStep.StepType(slug).label) for slug in STEP_FORMS],
        'assignments': task.assignments.select_related('student').order_by('student__name'),
        'assign_form': AssignStudentsForm(teacher=task.teacher, task=task) if can_manage and task.is_active else None,
        'can_manage': can_manage,
        'locked': task.is_locked,
    })


@login_required
def task_preview(request, pk):
    """The teacher sees every step as the child will, with no way to save anything."""
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    task = _task_or_404(request, pk)
    shown_practice = False
    items = []
    for step in task.steps.select_related('reading'):
        is_lectura = step.step_type == TaskStep.StepType.LECTURA
        # The reading practice widget is a single instance per page: only the first lectura step gets it.
        items.append({
            'step': step,
            'instruction': INSTRUCTIONS[_instruction_key(step)],
            'qid': f'task-question-{step.order}',
            'instruction_id': f'task-step-instruction-{step.order}',
            'hide_practice': is_lectura and shown_practice,
            **step_context(step, preview=True),
        })
        shown_practice = shown_practice or is_lectura
    return render(request, 'homework/teacher/task_preview.html', {
        'task': task,
        'items': items,
        'has_lectura': shown_practice,
        'kid_layout': True,
        'preview': True,
        'feedback': FEEDBACK,
        # Same keys as views_student._practice_context; empty save URL so nothing is ever written.
        'practice_save_url': '',
        'practice_reads': PRACTICE_READS,
        'practice_min_ms': MIN_READ_MS,
        'practice_max_ms': MAX_READ_MS,
    })


@login_required
@require_POST
def task_assign(request, pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    form = AssignStudentsForm(request.POST, teacher=request.user.teacher_profile, task=task)
    if form.is_valid():
        created = assign_students(task, form.selected_students())
        write_audit(request, 'assign_task', task, metadata={'created': created})
        if created:
            messages.success(request, f'Tarea asignada a {created} alumno(s).')
        else:
            messages.info(request, 'Esos alumnos ya tenían esta tarea.')
    else:
        for errors in form.errors.values():
            messages.error(request, errors[0])
    return redirect('homework:task_detail', pk=task.pk)


@login_required
@require_POST
def task_archive(request, pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    task.is_active = False
    task.save(update_fields=['is_active', 'updated_at'])
    write_audit(request, 'archive_task', task)
    messages.success(request, 'Tarea archivada.')
    return redirect('homework:task_list')


def _locked(request, task):
    messages.error(request, LOCKED)
    return redirect('homework:task_detail', pk=task.pk)


def _step_form_class_or_404(step_type):
    form_class = STEP_FORMS.get(step_type)
    if form_class is None:
        raise Http404
    return form_class


def _step_form_page(request, form, task, step_type, step=None):
    return render(request, 'homework/teacher/step_form.html', {
        'form': form,
        'task': task,
        'step': step,
        'step_type_label': TaskStep.StepType(step_type).label,
    })


@login_required
def step_create(request, pk, step_type):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    form_class = _step_form_class_or_404(step_type)
    with transaction.atomic():
        try:
            ensure_editable(task)
        except TaskLocked:
            return _locked(request, task)
        form = form_class(request.POST or None, request.FILES or None, task=task)
        if request.method == 'POST' and form.is_valid():
            step = append_step(task, step_type, form.to_payload(), **form.extras())
            write_audit(request, 'create_task_step', task, metadata={'step': step.pk, 'type': step_type})
            messages.success(request, 'Paso agregado.')
            return redirect('homework:task_detail', pk=task.pk)
        return _step_form_page(request, form, task, step_type)


@login_required
def step_update(request, pk, step_pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    with transaction.atomic():
        try:
            ensure_editable(task)
        except TaskLocked:
            return _locked(request, task)
        step = get_object_or_404(task.steps.select_related('reading'), pk=step_pk)
        form_class = _step_form_class_or_404(step.step_type)
        data = (request.POST, request.FILES) if request.method == 'POST' else (None, None)
        form = form_class(*data, task=task, step=step, initial=form_class.initial_from(step))
        if request.method == 'POST' and form.is_valid():
            update_step(step, form.to_payload(), **form.extras())
            write_audit(request, 'update_task_step', task, metadata={'step': step.pk})
            messages.success(request, 'Paso actualizado.')
            return redirect('homework:task_detail', pk=task.pk)
        return _step_form_page(request, form, task, step.step_type, step)


@login_required
@require_POST
def step_delete(request, pk, step_pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    with transaction.atomic():
        try:
            ensure_editable(task)
        except TaskLocked:
            return _locked(request, task)
        step = get_object_or_404(task.steps, pk=step_pk)
        delete_step(step)
        write_audit(request, 'delete_task_step', task, metadata={'step': step_pk})
    messages.success(request, 'Paso eliminado.')
    return redirect('homework:task_detail', pk=task.pk)


@login_required
@require_POST
def step_move(request, pk, step_pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk, active_only=True)
    direction = request.POST.get('direction')
    if direction not in ('up', 'down'):
        raise Http404
    with transaction.atomic():
        try:
            ensure_editable(task)
        except TaskLocked:
            return _locked(request, task)
        move_step(get_object_or_404(task.steps, pk=step_pk), direction)
    return redirect('homework:task_detail', pk=task.pk)


@login_required
@require_POST
def task_duplicate(request, pk):
    if not can_manage_tasks(request.user):
        return _deny(request)
    task = _task_or_404(request, pk)
    copy = duplicate_task(task)
    write_audit(request, 'duplicate_task', copy, metadata={'source': task.pk})
    messages.success(request, 'Tarea duplicada. Puedes cambiar sus pasos y asignarla.')
    return redirect('homework:task_detail', pk=copy.pk)


@login_required
def task_report(request, pk):
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    task = _task_or_404(request, pk)
    assignments = task.assignments.select_related('student').order_by('student__name', 'pk')
    page_obj = Paginator(assignments, RESOURCE_PAGE_SIZE).get_page(request.GET.get('page'))
    rows = task_rows(task, page_obj)
    can_view = difficulty_viewer(request.user)
    for row in rows:
        row['can_detail'] = can_view(row['student'])
        row['level'] = SnepaLevel(row['assignment'].snepa_level).label if row['can_detail'] and row['assignment'].snepa_level else ''
        if not row['can_detail']:
            # Ley 787: the break point and the errors are difficulty data, like the level.
            row['break_point'] = row['criteria'] = None
            row['errors'] = []
    return render(request, 'homework/teacher/task_report.html', {
        'task': task,
        'rows': rows,
        'page_obj': page_obj,
        'show_detail': any(row['can_detail'] for row in rows),
        'show_break_point': any(row['break_point'] for row in rows),
        'groups': break_point_groups(rows),
    })


@login_required
def dictation_instrument(request, pk, step_pk):
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    task = _task_or_404(request, pk)
    step = get_object_or_404(task.steps, pk=step_pk, step_type=TaskStep.StepType.DICTADO)
    assignments = task.assignments.select_related('student').order_by('student__name', 'pk')
    return render(request, 'homework/teacher/dictation_instrument.html', {
        'task': task,
        'step': step,
        'words': step.payload['words'],
        'sentences': step.payload['sentences'],
        'sheet': dictation_sheet(step, assignments, difficulty_viewer(request.user)),
    })


def _assignment_or_404(request, assignment_pk):
    assignment = get_object_or_404(TaskAssignment.objects.select_related('task', 'student'), pk=assignment_pk)
    # Ley 787: difficulty data only for admins and linked teachers with report permission.
    if not can_view_difficulty_data(request.user, assignment.student):
        raise Http404
    return assignment


@login_required
def assignment_report(request, assignment_pk):
    assignment = _assignment_or_404(request, assignment_pk)
    suggested = SnepaLevel(assignment.snepa_suggested).label if assignment.snepa_suggested else ''
    final = SnepaLevel(assignment.snepa_level).label if assignment.snepa_level else ''
    return render(request, 'homework/teacher/assignment_report.html', {
        'assignment': assignment,
        'task': assignment.task,
        'student': assignment.student,
        'can_view_task': can_view_task(request.user, assignment.task),
        'detail': assignment_detail(assignment),
        'suggested_label': suggested,
        'final_label': final,
        'override_form': SnepaOverrideForm(initial={'level': assignment.snepa_override}),
    })


@login_required
@require_POST
def assignment_level_update(request, assignment_pk):
    assignment = _assignment_or_404(request, assignment_pk)
    form = SnepaOverrideForm(request.POST)
    if form.is_valid():
        level = form.cleaned_data['level']
        if level in (assignment.snepa_override, assignment.snepa_level):
            return redirect('homework:assignment_report', assignment_pk=assignment.pk)
        teacher = getattr(request.user, 'teacher_profile', None)
        assignment.snepa_override = level
        assignment.snepa_override_by = teacher if level else None
        assignment.snepa_override_at = timezone.now() if level else None
        assignment.save(update_fields=['snepa_override', 'snepa_override_by', 'snepa_override_at'])
        write_audit(request, 'override_task_level', assignment, {'level': level, 'actor': request.user.pk})
        messages.success(request, 'Nivel actualizado.')
    else:
        messages.error(request, 'Elige un nivel válido.')
    return redirect('homework:assignment_report', assignment_pk=assignment.pk)
