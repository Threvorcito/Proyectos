"""FAS dictation: the 7 items of a dictado step and its break point (pure logic, computed on read)."""
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from django.db import models

from .payloads import DICTADO_SENTENCES, DICTADO_WORDS, BuildTarget
from .writing import split_units

if TYPE_CHECKING:
    from .models import StepResult

WORDS = DICTADO_WORDS
SENTENCES = DICTADO_SENTENCES
ITEMS = WORDS + SENTENCES
WORDS_ACHIEVED = 4  # spec §4: at least 4 of 5 words


class BreakPoint(models.TextChoices):
    INCOMPLETE = 'incomplete', 'Incompleto'
    SOUND_LETTER = 'sound_letter', 'Sonido-letra'
    WORDS = 'words', 'Palabras'
    SENTENCES = 'sentences', 'Oraciones'
    NONE = 'none', 'Sin quiebre'


@dataclass
class Criteria:
    sound_letter: bool
    words: bool
    sentences: bool


def item_target(payload: dict, item_index: int) -> BuildTarget:
    """Items 0-4 are the words (built with letters), 5-6 the sentences (built with words)."""
    if 0 <= item_index < WORDS:
        return BuildTarget('', payload['words'][item_index], '', 'letter')
    if WORDS <= item_index < ITEMS:
        return BuildTarget('', payload['sentences'][item_index - WORDS], '', 'word')
    raise IndexError(item_index)


def letter_ok(word: str, answer: str, letter: str) -> bool:
    """Whether every occurrence of ``letter`` in ``word`` survives in ``answer``.

    Units are aligned, not compared by index, so another missing letter ("mesa" -> "msa") does not count against
    the studied one; digraphs ("ll", "rr", "ch", "qu") are single units.
    """
    try:
        target = [unit.casefold() for unit in split_units(word, 'letter')]
        built = [unit.casefold() for unit in split_units(answer, 'letter')]
    except ValueError:
        return False
    letter = letter.casefold()
    equal = set()
    for tag, i1, i2, _j1, _j2 in SequenceMatcher(None, target, built, autojunk=False).get_opcodes():
        if tag == 'equal':
            equal.update(range(i1, i2))
    return all(i in equal for i, unit in enumerate(target) if unit == letter)


def score(payload: dict, results: 'Mapping[int, StepResult]') -> tuple[BreakPoint, Criteria | None]:
    """The break point is the first criterion not achieved, in FAS order; ``results`` is keyed by item index."""
    items = [results.get(index) for index in range(ITEMS)]
    if any(result is None or result.completed_at is None for result in items):
        return BreakPoint.INCOMPLETE, None
    words, sentences = items[:WORDS], items[WORDS:]
    letter = payload['letter']
    criteria = Criteria(
        sound_letter=sum(
            letter_ok(word, result.first_answer, letter) for word, result in zip(payload['words'], words)
        ) >= WORDS_ACHIEVED,
        words=sum(bool(result.first_try_correct) for result in words) >= WORDS_ACHIEVED,
        sentences=not any(result.modeled for result in sentences),
    )
    if not criteria.sound_letter:
        return BreakPoint.SOUND_LETTER, criteria
    if not criteria.words:
        return BreakPoint.WORDS, criteria
    if not criteria.sentences:
        return BreakPoint.SENTENCES, criteria
    return BreakPoint.NONE, criteria
