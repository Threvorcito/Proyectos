from functools import wraps

from django.contrib.auth.decorators import login_required
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from core.json_payload import parse_json_object

from .copy import FEEDBACK, INSTRUCTIONS
from .decoding import decode_word
from .evaluation import InvalidAnswer, is_build_step
from .models import StepResult, TaskAssignment, TaskStep
from .payloads import build_target
from .phonemes import audio_for
from readings.services import MAX_READ_MS, MIN_READ_MS, PRACTICE_READS

from .services import ItemClosed, mark_item_done, record_decode_help, start_assignment, step_states, submit_answer
from .writing import build_tiles, split_units


def _student_only(view):
    """Children only: everyone else goes back to their own dashboard."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        student = getattr(request.user, 'student_profile', None)
        if student is None:
            return redirect('dashboard:redirect')
        return view(request, student, *args, **kwargs)

    return wrapper


def _assignment_for(student, assignment_pk):
    # Archived tasks and tasks without steps are invisible to the child.
    has_steps = TaskStep.objects.filter(task=OuterRef('task_id'))
    queryset = TaskAssignment.objects.select_related('task').filter(Exists(has_steps))
    return get_object_or_404(queryset, pk=assignment_pk, student=student, task__is_active=True)


def _path_url(assignment, *, done=False):
    url = reverse('homework:student_task', args=[assignment.pk])
    return f'{url}?hecho=1' if done else url


def _instruction_key(step):
    if step.step_type == TaskStep.StepType.ARMA and '[' in step.payload.get('text', ''):
        return 'arma_blank'
    if step.step_type == TaskStep.StepType.CONTESTA and step.payload.get('kind') == 'build':
        return 'contesta_build'
    return step.step_type


def step_context(step, *, preview=False):
    """Per-step render context shared by the child page and the teacher preview.

    Build steps get their tiles. The shuffle is seeded from the task and step ids (the
    preview has no assignment), so a reload never reshuffles and the teacher sees the child's order.
    ``preview`` also hands the target units to the page so the preview can mimic the feedback;
    the child page never receives them.
    """
    if not is_build_step(step):
        return {}
    target = build_target(step.step_type, step.payload)
    units = split_units(target.text, target.unit)
    build = {
        'before': target.before,
        'after': target.after,
        'has_blank': bool(target.before or target.after),
        'unit': target.unit,
        'tiles': build_tiles(units, target.unit, seed=step.task_id * 1000 + step.pk),
        'listen_text': target.full_text,
    }
    if preview:
        sounds = decode_word(target.text)['letters'] if target.unit == 'letter' else []
        aligned = len(sounds) == len(units)
        preview_units = []
        for i, unit in enumerate(units):
            if aligned and sounds[i]['say']:
                preview_units.append({'text': unit, 'say': sounds[i]['say'], 'audio': sounds[i]['audio']})
            else:
                preview_units.append({'text': unit, 'say': unit, 'audio': audio_for(unit)})
        build['preview_units'] = preview_units
        build['preview_model'] = target.full_text
    return {'build': build}


@_student_only
def student_task(request, student, assignment_pk):
    assignment = _assignment_for(student, assignment_pk)
    states = step_states(assignment)
    current = next((state for state in states if state.current), None)
    return render(request, 'homework/student/task_path.html', {
        'assignment': assignment,
        'states': states,
        'current': current,
        'completed': current is None,
        'just_done': request.GET.get('hecho') == '1',
        'feedback': FEEDBACK,
    })


@_student_only
def student_step(request, student, assignment_pk, order):
    assignment = _assignment_for(student, assignment_pk)
    step = get_object_or_404(assignment.task.steps, order=order)
    start_assignment(assignment)
    current = next((state for state in step_states(assignment) if state.current), None)
    if current is None or current.step.pk != step.pk:
        return redirect(_path_url(assignment))
    kwargs = {'assignment_pk': assignment.pk, 'order': step.order}
    return render(request, 'homework/student/step.html', {
        **_practice_context(student, step),
        **step_context(step),
        'step': step,
        'assignment': assignment,
        'instruction': INSTRUCTIONS[_instruction_key(step)],
        'preview': False,
        'done_url': reverse('homework:step_done', kwargs=kwargs),
        'answer_url': reverse('homework:step_answer', kwargs=kwargs),
        'help_url': reverse('homework:decode_help', args=[assignment.pk]),
        'done_items': _done_items(assignment, step),
        'feedback': FEEDBACK,
    })


def _done_items(assignment, step):
    """Palabras the child already finished, so their cards come back starred."""
    if step.step_type != TaskStep.StepType.PALABRAS:
        return set()
    rows = StepResult.objects.filter(assignment=assignment, step=step, completed_at__isnull=False)
    return set(rows.values_list('item_index', flat=True))


def _practice_context(student, step):
    """Settings for the reused "Practicar lectura"; progress is saved only for a same-grade library reading."""
    if step.step_type != TaskStep.StepType.LECTURA:
        return {}
    reading = step.reading
    saves = reading is not None and reading.is_active and reading.grade == student.grade
    return {
        'practice_save_url': reverse('readings:save_practice_attempt', args=[reading.pk]) if saves else '',
        'practice_reads': PRACTICE_READS,
        'practice_min_ms': MIN_READ_MS,
        'practice_max_ms': MAX_READ_MS,
    }


def _item_index(body):
    # Not core.json_payload.parse_id: it rejects 0, which is the first item.
    value = body.get('item_index')
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _outcome_response(assignment, outcome):
    return JsonResponse({
        'status': outcome.status,
        'hint': outcome.hint,
        'model_answer': outcome.model_answer,
        'step_done': outcome.step_done,
        'task_done': outcome.task_done,
        'next_url': _path_url(assignment, done=True) if outcome.step_done else None,
    })


def _rejected(reason, status):
    return JsonResponse({'saved': False, 'reason': reason}, status=status)


def _json_step_action(request, student, assignment_pk, order, action):
    assignment = _assignment_for(student, assignment_pk)
    try:
        step = assignment.task.steps.get(order=order)
    except TaskStep.DoesNotExist:
        return _rejected('step', 404)
    state = next(s for s in step_states(assignment) if s.step.pk == step.pk)
    if not (state.current or state.done):
        return _rejected('step', 400)
    body = parse_json_object(request)
    item_index = _item_index(body) if body is not None else None
    if item_index is None:
        return _rejected('payload', 400)
    try:
        outcome = action(assignment, step, item_index, body)
    except InvalidAnswer:
        return _rejected('payload', 400)
    except ItemClosed:
        # Double tap or second tab: nothing is lost, the page just moves on.
        return JsonResponse({
            'saved': False,
            'reason': 'closed',
            'step_done': True,
            'next_url': _path_url(assignment, done=True),
        }, status=409)
    return _outcome_response(assignment, outcome)


@require_POST
@_student_only
def step_done(request, student, assignment_pk, order):
    return _json_step_action(
        request, student, assignment_pk, order,
        lambda assignment, step, index, body: mark_item_done(assignment, step, index),
    )


@require_POST
@_student_only
def step_answer(request, student, assignment_pk, order):
    return _json_step_action(
        request, student, assignment_pk, order,
        lambda assignment, step, index, body: submit_answer(
            assignment, step, index, {key: body[key] for key in ('choice', 'tiles') if key in body}
        ),
    )


@require_POST
@_student_only
def decode_help(request, student, assignment_pk):
    """The child tapped a word to hear its sounds: log it for the teacher, never for anyone else."""
    assignment = _assignment_for(student, assignment_pk)
    body = parse_json_object(request)
    word = body.get('word') if body is not None else None
    step_order = body.get('step_order') if body is not None else None
    if not isinstance(word, str) or not word.strip():
        return JsonResponse({'saved': False, 'reason': 'payload'}, status=400)
    if step_order is not None and (isinstance(step_order, bool) or not isinstance(step_order, int)):
        return JsonResponse({'saved': False, 'reason': 'payload'}, status=400)
    step = assignment.task.steps.filter(order=step_order).first() if step_order is not None else None
    record_decode_help(assignment, step, word)
    return JsonResponse({'saved': True})
