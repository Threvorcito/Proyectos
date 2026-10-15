from typing import Iterable

from django.db import transaction
from django.db.models import Max

from learning.models import StudentProfile, TeacherProfile

from .models import Task, TaskAssignment, TaskStep


def group_students(teacher: TeacherProfile, grade: str):
    return teacher.students.filter(grade=grade)


def assign_students(task: Task, students: Iterable[StudentProfile]) -> int:
    """Create the missing assignments for the teacher's own students; return how many were created."""
    allowed = set(task.teacher.students.values_list('pk', flat=True))
    wanted = {student.pk for student in students} & allowed
    existing = set(task.assignments.filter(student_id__in=wanted).values_list('student_id', flat=True))
    created = TaskAssignment.objects.bulk_create(
        TaskAssignment(task=task, student_id=pk) for pk in sorted(wanted - existing)
    )
    return len(created)


class TaskLocked(Exception):
    """The task already has a student who started it, so its steps are frozen."""


def ensure_editable(task: Task) -> None:
    """Raise TaskLocked once a student started the task.

    Call it inside ``transaction.atomic()`` and keep the transaction open while
    mutating: the task and assignment rows stay locked until commit, so a student
    cannot start the task between this check and the write.
    """
    with transaction.atomic():
        Task.objects.select_for_update().get(pk=task.pk)
        started = TaskAssignment.objects.select_for_update().filter(task=task, started_at__isnull=False)
        if started.exists():
            raise TaskLocked(task.pk)


def _validated_step(step: TaskStep) -> TaskStep:
    step.full_clean(exclude=['task', 'order'])
    return step


@transaction.atomic
def append_step(task: Task, step_type: str, payload: dict, *, image=None, reading=None) -> TaskStep:
    last = task.steps.aggregate(last=Max('order'))['last'] or 0
    step = TaskStep(task=task, order=last + 1, step_type=step_type, payload=payload, image=image, reading=reading)
    _validated_step(step).save()
    return step


@transaction.atomic
def update_step(step: TaskStep, payload: dict, *, image=None, reading=None) -> TaskStep:
    """Replace the payload; a new image replaces the old one, ``reading`` is always applied."""
    step.payload = payload
    step.reading = reading
    if image:
        step.image = image
    _validated_step(step).save()
    return step


@transaction.atomic
def delete_step(step: TaskStep) -> None:
    task_id = step.task_id
    step.delete()
    for order, other in enumerate(TaskStep.objects.filter(task_id=task_id).order_by('order'), start=1):
        if other.order != order:
            other.order = order
            other.save(update_fields=['order'])


@transaction.atomic
def move_step(step: TaskStep, direction: str) -> None:
    if direction not in ('up', 'down'):
        raise ValueError(direction)
    step_order = step.order
    target = step_order - 1 if direction == 'up' else step_order + 1
    neighbour = TaskStep.objects.filter(task_id=step.task_id, order=target).first()
    if neighbour is None:
        return
    # Order 0 is free, so the unique (task, order) constraint holds at every statement.
    TaskStep.objects.filter(pk=step.pk).update(order=0)
    TaskStep.objects.filter(pk=neighbour.pk).update(order=step_order)
    TaskStep.objects.filter(pk=step.pk).update(order=target)
    step.order = target


COPY_SUFFIX = ' (copia)'


@transaction.atomic
def duplicate_task(task: Task) -> Task:
    limit = Task._meta.get_field('title').max_length - len(COPY_SUFFIX)
    copy = Task.objects.create(
        teacher=task.teacher,
        subject=task.subject,
        grade=task.grade,
        title=f'{task.title[:limit]}{COPY_SUFFIX}',
        lesson_plan=task.lesson_plan,
    )
    TaskStep.objects.bulk_create(
        TaskStep(
            task=copy,
            order=step.order,
            step_type=step.step_type,
            payload=step.payload,
            image=step.image.name or None,
            reading=step.reading,
        )
        for step in task.steps.all()
    )
    return copy
