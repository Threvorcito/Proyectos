from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dashboard.views import RESOURCE_PAGE_SIZE, is_admin_user, write_audit

from readings.services import MAX_READ_MS, MIN_READ_MS, PRACTICE_READS

from .copy import FEEDBACK, INSTRUCTIONS
from .forms import STEP_FORMS, AssignStudentsForm, TaskForm
from .models import Task, TaskStep
from .permissions import can_manage_tasks, can_view_task
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
