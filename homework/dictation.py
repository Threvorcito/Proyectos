"""FAS dictation: the 7 items of a dictado step and its break point (pure logic, computed on read)."""
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING

from django.db import models

from .payloads import DICTADO_SENTENCES, DICTADO_WORDS, BuildTarget
from .writing import _PLAIN, split_units

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


class ErrorType(models.TextChoices):
    """Error types of the MINED Tomo I (Educación Especial), p102-109 and p130."""
    OMISSION = 'omission', 'Omisión'
    CONFUSION = 'confusion', 'Confusión'
    INVERSION = 'inversion', 'Inversión'
    SUBSTITUTION = 'substitution', 'Sustitución'
    ADDITION = 'addition', 'Agrega'


# Tome p102, p106, p107; m-n and u-n as in writing.CONFUSABLE.
CONFUSABLE_PAIRS = frozenset(frozenset(pair) for pair in ('bd', 'pq', 'mn', 'mw', 'pb', 'un', 'lt'))


@dataclass
class DictationError:
    kind: ErrorType
    detail: str  # the missing unit for an omission, the pair "a–b" for a confusion, '' otherwise


def _plain(unit: str) -> str:
    return unit.casefold().translate(_PLAIN)


def classify(target: str, answer: str, unit: str) -> list[DictationError]:
    """The errors of ``answer`` against ``target``, ignoring case and accents; ``unit`` is 'letter' or 'word'."""
    target_units = split_units(target, unit)
    try:
        answer_units = split_units(answer, unit)
    except ValueError:
        answer_units = []
    expected = [_plain(item) for item in target_units]
    built = [_plain(item) for item in answer_units]
    if expected == built:
        return []
    if not built:
        return [DictationError(ErrorType.OMISSION, '')]
    if sorted(expected) == sorted(built):
        return [DictationError(ErrorType.INVERSION, '')]
    errors = []
    for tag, i1, i2, j1, j2 in SequenceMatcher(None, expected, built, autojunk=False).get_opcodes():
        if tag == 'delete':
            errors += [DictationError(ErrorType.OMISSION, item.casefold()) for item in target_units[i1:i2]]
        elif tag == 'insert':
            errors.append(DictationError(ErrorType.ADDITION, ''))
        elif tag == 'replace' and i2 - i1 == j2 - j1:
            for want, got in zip(expected[i1:i2], built[j1:j2]):
                if frozenset((want, got)) in CONFUSABLE_PAIRS:
                    errors.append(DictationError(ErrorType.CONFUSION, '–'.join(sorted((want, got)))))
                else:
                    errors.append(DictationError(ErrorType.SUBSTITUTION, ''))
        elif tag == 'replace':
            errors.append(DictationError(ErrorType.SUBSTITUTION, ''))
    return errors


def _error_label(error: DictationError) -> str:
    if error.kind == ErrorType.OMISSION and error.detail:
        return f'{error.kind.label} «{error.detail}»'
    if error.kind == ErrorType.CONFUSION:
        return f'{error.kind.label} {error.detail}'
    return error.kind.label


def error_summary(payload: dict, results: 'Mapping[int, StepResult]') -> list[tuple[str, int]]:
    """Error labels with counts over the completed items' first answers, most frequent first."""
    counts = Counter()
    for index in range(ITEMS):
        result = results.get(index)
        if result is None or result.completed_at is None:
            continue
        target = item_target(payload, index)
        counts.update(_error_label(error) for error in classify(target.text, result.first_answer, target.unit))
    return counts.most_common()
