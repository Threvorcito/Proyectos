"""Teacher-side read models for a task: progress rows and one child's difficulty detail."""
from collections import Counter

from .models import TaskStep
from .services import step_states


def task_rows(task) -> list[dict]:
    assignments = task.assignments.select_related('student', 'task').order_by('student__name')
    rows = []
    for assignment in assignments:
        states = step_states(assignment)
        rows.append({
            'assignment': assignment,
            'student': assignment.student,
            'status': assignment.get_status_display(),
            'steps_done': sum(1 for state in states if state.done),
            'steps_total': len(states),
        })
    return rows


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
