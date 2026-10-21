"""Daily FAS class: one ready-made task per letter, built from the lesson content bank."""
from django.db import transaction
from django.db.models import Exists, OuterRef

from learning.models import StudentProfile, Subject, TeacherProfile

from .fas_content import lesson_for
from .models import Task, TaskAssignment, TaskStep
from .phonemes import SOUND_TABLE, STOPS
from .services import append_step

CREATED = 'created'
ASSIGNED = 'assigned'


def _sound(letter: str) -> str:
    """What the child hears: the elongated continuant, or a stop said with "a" ("pa")."""
    if SOUND_TABLE.get(letter):
        return SOUND_TABLE[letter]
    return f'{letter}a' if letter in STOPS else letter


@transaction.atomic
def build_daily_class(teacher: TeacherProfile, letter: str, subject: Subject) -> Task:
    """Create the six-step FAS class for ``letter``; ValueError when the bank has no lesson for it."""
    lesson = lesson_for(letter)
    if lesson is None:
        raise ValueError(f'No FAS lesson for {letter!r}')
    task = Task.objects.create(
        teacher=teacher, subject=subject, grade=StudentProfile.Grade.FIRST, title=f'Clase FAS de la «{letter}»',
    )
    words = list(lesson.words)
    sentences = list(lesson.sentences)
    append_step(task, TaskStep.StepType.MIRA, {
        'question': f'El sonido de hoy: {_sound(letter)}. ¿Qué palabras tienen este sonido?',
    })
    append_step(task, TaskStep.StepType.PALABRAS, {'words': words})
    append_step(task, TaskStep.StepType.ARMA, {'text': lesson.build_word, 'unit': 'syllable'})
    append_step(task, TaskStep.StepType.ARMA, {'text': sentences[0], 'unit': 'word'})
    append_step(task, TaskStep.StepType.LECTURA, {'text': lesson.reading})
    append_step(task, TaskStep.StepType.DICTADO, {'letter': letter, 'words': words[:5], 'sentences': sentences})
    return task


def letter_statuses(teacher: TeacherProfile) -> dict[str, str]:
    """``'created'`` or ``'assigned'`` per dictado letter of the teacher's active tasks (assigned wins); one query."""
    dictados = TaskStep.objects.filter(
        task__teacher=teacher, task__is_active=True, step_type=TaskStep.StepType.DICTADO,
    ).annotate(
        assigned=Exists(TaskAssignment.objects.filter(task=OuterRef('task'))),
    ).values_list('payload', 'assigned')
    statuses = {}
    for payload, assigned in dictados:
        letter = payload.get('letter')
        if assigned or statuses.get(letter) != ASSIGNED:
            statuses[letter] = ASSIGNED if assigned else CREATED
    return statuses
