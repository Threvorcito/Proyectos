import unicodedata
from dataclasses import dataclass
from typing import Iterable

from django.db import transaction
from django.db.models import Exists, F, Max, OuterRef
from django.utils import timezone

from learning.models import StudentProfile, TeacherProfile

from .evaluation import InvalidAnswer, evaluate
from .levels import suggest_for_assignment
from .models import DecodeHelpEvent, OmissionEvent, StepResult, Task, TaskAssignment, TaskStep


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


MAX_ATTEMPTS = 2
TASK_POINTS = 10
TASK_STARS = 1

EVALUATED_STEP_TYPES = {TaskStep.StepType.CONTESTA, TaskStep.StepType.ARMA, TaskStep.StepType.EJEMPLO}


class ItemClosed(Exception):
    """The item was already completed; further answers are ignored."""


@dataclass
class ItemOutcome:
    status: str  # 'done' | 'correct' | 'try_again' | 'modeled'
    hint: dict | None
    model_answer: str
    step_done: bool
    task_done: bool


@dataclass
class StepState:
    step: TaskStep
    done: bool
    current: bool


def item_index_valid(step: TaskStep, item_index: int) -> bool:
    return isinstance(item_index, int) and 0 <= item_index < step.item_count


def next_assignment_for(student: StudentProfile) -> TaskAssignment | None:
    has_steps = TaskStep.objects.filter(task=OuterRef('task_id'))
    return (
        TaskAssignment.objects.filter(student=student, task__is_active=True)
        .exclude(status=TaskAssignment.Status.COMPLETED)
        .filter(Exists(has_steps))
        .select_related('task')
        .order_by(F('task__due_date').asc(nulls_last=True), 'assigned_at')
        .first()
    )


def _lock_assignment(assignment: TaskAssignment) -> TaskAssignment:
    return TaskAssignment.objects.select_for_update().get(pk=assignment.pk)


def start_assignment(assignment: TaskAssignment) -> None:
    """Mark the assignment as started once.

    The task row is locked first (the same row ``ensure_editable`` locks), so a
    teacher edit and a child start cannot interleave.
    """
    with transaction.atomic():
        Task.objects.select_for_update().get(pk=assignment.task_id)
        locked = _lock_assignment(assignment)
        if locked.started_at is None:
            locked.started_at = timezone.now()
            if locked.status == TaskAssignment.Status.ASSIGNED:
                locked.status = TaskAssignment.Status.IN_PROGRESS
            locked.save(update_fields=['started_at', 'status'])
    assignment.started_at = locked.started_at
    assignment.status = locked.status


def _done_counts(assignment: TaskAssignment) -> dict[int, int]:
    rows = StepResult.objects.filter(assignment=assignment, completed_at__isnull=False)
    counts: dict[int, set[int]] = {}
    for step_id, item_index in rows.values_list('step_id', 'item_index'):
        counts.setdefault(step_id, set()).add(item_index)
    return {step_id: len(indexes) for step_id, indexes in counts.items()}


def step_states(assignment: TaskAssignment) -> list[StepState]:
    counts = _done_counts(assignment)
    states, current_found = [], False
    for step in assignment.task.steps.all():
        done = counts.get(step.pk, 0) >= step.item_count
        current = not done and not current_found
        current_found = current_found or current
        states.append(StepState(step=step, done=done, current=current))
    return states


def current_step(assignment: TaskAssignment) -> TaskStep | None:
    return next((state.step for state in step_states(assignment) if state.current), None)


def _check_target(assignment: TaskAssignment, step: TaskStep, item_index: int) -> None:
    if step.task_id != assignment.task_id or not item_index_valid(step, item_index):
        raise InvalidAnswer('item')


def _finish(assignment: TaskAssignment, step: TaskStep) -> tuple[bool, bool]:
    states = step_states(assignment)
    step_done = next((s.done for s in states if s.step.pk == step.pk), False)
    task_done = all(s.done for s in states)
    if task_done:
        complete_assignment(assignment)
    return step_done, task_done


def mark_item_done(assignment: TaskAssignment, step: TaskStep, item_index: int) -> ItemOutcome:
    """Close a non-evaluated item (mira, lectura, palabras); idempotent."""
    if step.step_type in EVALUATED_STEP_TYPES:
        raise InvalidAnswer(step.step_type)
    _check_target(assignment, step, item_index)
    with transaction.atomic():
        _lock_assignment(assignment)
        result, _ = StepResult.objects.get_or_create(assignment=assignment, step=step, item_index=item_index)
        if result.completed_at is None:
            result.completed_at = timezone.now()
            result.save(update_fields=['completed_at'])
        step_done, task_done = _finish(assignment, step)
    return ItemOutcome('done', None, '', step_done, task_done)


def submit_answer(assignment: TaskAssignment, step: TaskStep, item_index: int, payload: dict) -> ItemOutcome:
    _check_target(assignment, step, item_index)
    with transaction.atomic():
        _lock_assignment(assignment)
        result, _ = StepResult.objects.get_or_create(assignment=assignment, step=step, item_index=item_index)
        if result.completed_at is not None:
            raise ItemClosed((step.pk, item_index))
        evaluation = evaluate(step, item_index, payload)
        result.attempts += 1
        if result.attempts == 1:
            result.first_answer = evaluation.answer_text
            result.first_try_correct = evaluation.correct
        result.answer = evaluation.answer_text
        for position, missing_unit in evaluation.omissions:
            OmissionEvent(
                assignment=assignment, step=step, target=evaluation.target, missing_unit=missing_unit, position=position
            ).save()
        hint, model_answer = None, ''
        if evaluation.correct:
            status = 'correct'
        elif result.attempts < MAX_ATTEMPTS:
            status, hint = 'try_again', evaluation.hint
            result.hints_used += 1
        else:
            status, model_answer = 'modeled', evaluation.model_answer
            result.modeled = True
        if status != 'try_again':
            result.completed_at = timezone.now()
        result.save()
        step_done, task_done = (False, False) if status == 'try_again' else _finish(assignment, step)
    return ItemOutcome(status, hint, model_answer, step_done, task_done)


def record_decode_help(assignment: TaskAssignment, step: TaskStep | None, word: str) -> DecodeHelpEvent:
    """Log that the child asked to hear a word's sounds; the word is stored lowercase, at most 80 characters."""
    event = DecodeHelpEvent(
        assignment=assignment,
        step=step,
        word=unicodedata.normalize('NFC', word).strip().lower()[:80],
    )
    event.save()  # not bulk_create: DecodeHelpEvent.save() enforces the length
    return event


def complete_assignment(assignment: TaskAssignment) -> int:
    """Close the assignment and award the reward once; return the points awarded."""
    now = timezone.now()
    with transaction.atomic():
        locked = _lock_assignment(assignment)
        student = StudentProfile.objects.select_for_update().get(pk=locked.student_id)
        if locked.completed_at is not None or not all(s.done for s in step_states(locked)):
            return 0
        locked.status = TaskAssignment.Status.COMPLETED
        locked.completed_at = now
        locked.points_awarded = TASK_POINTS
        locked.snepa_suggested = suggest_for_assignment(locked)
        locked.save(update_fields=['status', 'completed_at', 'points_awarded', 'snepa_suggested'])
        StudentProfile.objects.filter(pk=student.pk).update(
            points=F('points') + TASK_POINTS,
            stars=F('stars') + TASK_STARS,
            experience=F('experience') + TASK_POINTS,
            last_activity_at=now,
        )
    assignment.status = locked.status
    assignment.completed_at = now
    assignment.points_awarded = TASK_POINTS
    return TASK_POINTS
