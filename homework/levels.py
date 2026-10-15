"""Suggested SNEPA level (MINED scale) from first tries and helps; the teacher can override it."""
from .models import SnepaLevel, TaskStep


def suggest_snepa(evaluated: int, first_try_correct: int, helps: int) -> str:
    if evaluated <= 0:
        return ''
    accuracy = first_try_correct / evaluated
    help_rate = helps / evaluated
    if accuracy >= 0.9 and help_rate <= 0.25:
        return SnepaLevel.ADVANCED.value
    if accuracy >= 0.7 and help_rate <= 0.75:
        return SnepaLevel.SATISFACTORY.value
    if accuracy >= 0.4:
        return SnepaLevel.FUNDAMENTAL.value
    return SnepaLevel.INITIAL.value


def suggest_for_assignment(assignment) -> str:
    """Decoding help on a palabras step is the exercise itself, so it is not counted as a help."""
    results = list(assignment.results.all())
    evaluated = [r for r in results if r.first_try_correct is not None]
    helps = sum(r.hints_used for r in results) + sum(1 for r in results if r.modeled)
    helps += assignment.decode_helps.exclude(step__step_type=TaskStep.StepType.PALABRAS).count()
    return suggest_snepa(len(evaluated), sum(1 for r in evaluated if r.first_try_correct), helps)
