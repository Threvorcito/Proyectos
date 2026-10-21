"""Teacher-side read models for a task: progress rows and one child's difficulty detail."""
from collections import Counter

from . import dictation
from .dictation import BreakPoint
from .models import StepResult, TaskStep


GROUP_ORDER = (BreakPoint.SOUND_LETTER, BreakPoint.WORDS, BreakPoint.SENTENCES, BreakPoint.INCOMPLETE, BreakPoint.NONE)


def _dictado_step(steps):
    return next((step for step in steps if step.step_type == TaskStep.StepType.DICTADO), None)


def task_rows(task, assignments) -> list[dict]:
    """Rows for the given assignments (one page); a fixed number of queries however many there are.

    ``break_point`` and ``criteria`` come from the task's first dictado step (None when it has none).
    """
    assignments = list(assignments)
    steps = list(task.steps.all())
    dictado = _dictado_step(steps)
    done_items: dict[tuple[int, int], set[int]] = {}
    dictado_results: dict[int, dict[int, StepResult]] = {}
    for result in StepResult.objects.filter(assignment__in=assignments):
        if result.completed_at is not None:
            done_items.setdefault((result.assignment_id, result.step_id), set()).add(result.item_index)
        if dictado is not None and result.step_id == dictado.pk:
            dictado_results.setdefault(result.assignment_id, {})[result.item_index] = result
    rows = []
    for assignment in assignments:
        break_point, criteria = (
            dictation.score(dictado.payload, dictado_results.get(assignment.pk, {})) if dictado else (None, None)
        )
        rows.append({
            'assignment': assignment,
            'student': assignment.student,
            'status': assignment.get_status_display(),
            'steps_done': sum(1 for step in steps if len(done_items.get((assignment.pk, step.pk), ())) >= step.item_count),
            'steps_total': len(steps),
            'break_point': break_point,
            'criteria': criteria,
        })
    return rows


def break_point_groups(rows) -> list[tuple[str, list]]:
    """Students grouped by break point in FAS order, so the teacher can reinforce each group together."""
    groups = [(point, [row['student'] for row in rows if row['break_point'] == point]) for point in GROUP_ORDER]
    return [(point.label, students) for point, students in groups if students]


def dictation_sheet(step, assignments, can_view) -> list[dict]:
    """One instrument row per assignment: the 7 items pre-marked from the app, the criteria and the break point.

    Students whose difficulty data the viewer may not see (Ley 787) get a blank row for paper use.
    """
    assignments = list(assignments)
    results: dict[int, dict[int, StepResult]] = {}
    for result in StepResult.objects.filter(assignment__in=assignments, step=step):
        results.setdefault(result.assignment_id, {})[result.item_index] = result
    sheet = []
    for assignment in assignments:
        row = {'student': assignment.student, 'marks': [None] * dictation.ITEMS, 'criteria': None, 'break_point': None}
        if can_view(assignment.student):
            items = results.get(assignment.pk, {})
            row['marks'] = [
                items[index].first_try_correct if index in items and items[index].completed_at else None
                for index in range(dictation.ITEMS)
            ]
            row['break_point'], row['criteria'] = dictation.score(step.payload, items)
        sheet.append(row)
    return sheet


def _prompt(step, item_index) -> str:
    payload = step.payload
    if step.step_type == TaskStep.StepType.PALABRAS:
        words = payload.get('words', [])
        return words[item_index] if item_index < len(words) else ''
    if step.step_type == TaskStep.StepType.EJEMPLO:
        exercises = payload.get('exercises', [])
        return exercises[item_index].get('prompt', '') if item_index < len(exercises) else ''
    return payload.get('question') or payload.get('text') or ''


def assignment_detail(assignment) -> dict:
    results = assignment.results.select_related('step').order_by('step__order', 'item_index')
    answers = [{
        'step_type': result.step.get_step_type_display(),
        'prompt': _prompt(result.step, result.item_index),
        'first_answer': result.first_answer,
        'answer': result.answer,
        'first_try_correct': result.first_try_correct,
        'hints_used': result.hints_used,
        'modeled': result.modeled,
    } for result in results]
    decode_words = Counter(assignment.decode_helps.values_list('word', flat=True)).most_common()
    omissions = Counter(assignment.omissions.values_list('target', 'missing_unit'))
    return {
        'answers': answers,
        'decode_words': decode_words,
        'omissions': [(target, unit, count) for (target, unit), count in omissions.most_common()],
    }
