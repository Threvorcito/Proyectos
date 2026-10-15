from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from dashboard.views import RESOURCE_PAGE_SIZE, is_admin_user, write_audit

from .forms import AssignStudentsForm, TaskForm
from .models import Task
from .permissions import can_manage_tasks, can_view_task
from .services import assign_students

DENIED = 'No tienes permiso para gestionar tareas.'


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


@login_required
def task_detail(request, pk):
    if not (is_admin_user(request.user) or can_manage_tasks(request.user)):
        return _deny(request)
    task = _task_or_404(request, pk)
    can_manage = can_manage_tasks(request.user)
    return render(request, 'homework/teacher/task_detail.html', {
        'task': task,
        'steps': task.steps.select_related('reading'),
        'assignments': task.assignments.select_related('student').order_by('student__name'),
        'assign_form': AssignStudentsForm(teacher=task.teacher, task=task) if can_manage and task.is_active else None,
        'can_manage': can_manage,
        'locked': task.is_locked,
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
