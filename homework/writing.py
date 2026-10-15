"""Tiles, distractors and omission detection for assisted writing (pure Python)."""
import random
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from .syllables import WORD, split_syllables, word_units

BUILD_MAX_UNITS = 12
CONFUSABLE = {'b': 'd', 'd': 'b', 'p': 'q', 'q': 'p', 'm': 'n', 'n': 'm', 'u': 'n'}
FILLER_WORDS = ('el', 'la', 'los', 'un', 'una')
_LETTER_POOL = 'bdpqmnaeiou'
_SYLLABLE_POOL = ('ma', 'sa', 'la', 'ta', 'pa', 'na', 'lo', 'so', 'to', 'ne')
_VOWEL_CYCLE = {'a': 'e', 'e': 'i', 'i': 'o', 'o': 'u', 'u': 'a'}
_PLAIN = str.maketrans('áéíóú', 'aeiou')
MISSING_UNIT_MAX = 30  # matches the model field cap


def split_units(text, unit):
    if unit == 'word':
        return WORD.findall(text)
    words = WORD.findall(text)
    if len(words) != 1:
        raise ValueError('letter and syllable targets must be a single word')
    if unit == 'letter':
        return [u.text for u in word_units(words[0])]
    if unit == 'syllable':
        return split_syllables(words[0])
    raise ValueError(f'unknown unit: {unit}')


def _swap_confusable(text):
    for i, char in enumerate(text):
        other = CONFUSABLE.get(char.lower())
        if other:
            return text[:i] + (other.upper() if char.isupper() else other) + text[i + 1:]
    return None


def _shift_vowel(text):
    for i, char in enumerate(text):
        base = char.lower().translate(_PLAIN)
        if base in _VOWEL_CYCLE:
            nxt = _VOWEL_CYCLE[base]
            return text[:i] + (nxt.upper() if char.isupper() else nxt) + text[i + 1:]
    return None


def _candidates(units, unit):
    for text in units:
        swapped = _swap_confusable(text)
        if swapped:
            yield swapped
        shifted = text
        for _ in range(4):
            shifted = _shift_vowel(shifted)
            if not shifted:
                break
            yield shifted
    yield from {'word': FILLER_WORDS, 'syllable': _SYLLABLE_POOL}.get(unit, _LETTER_POOL)


def build_tiles(units, unit, seed):
    wanted = 2 if len(units) <= 2 else 3
    taken = {u.casefold() for u in units}
    distractors = []
    for cand in _candidates(units, unit):
        if cand.casefold() not in taken:
            taken.add(cand.casefold())
            distractors.append(cand)
            if len(distractors) == wanted:
                break
    tiles = list(units) + distractors
    random.Random(seed).shuffle(tiles)
    return tiles


@dataclass
class BuildCheck:
    status: str
    missing: list = field(default_factory=list)
    hole_index: int | None = None


def check_build(target, answer):
    a = [u.casefold() for u in target]
    b = [u.casefold() for u in answer]
    if a == b:
        return BuildCheck('correct', [], None)
    ops = SequenceMatcher(None, a, b, autojunk=False).get_opcodes()
    if all(tag in ('equal', 'delete') for tag, *_ in ops) and any(t == 'delete' for t, *_ in ops):
        missing = [
            (i, target[i][:MISSING_UNIT_MAX])
            for tag, i1, i2, _j1, _j2 in ops if tag == 'delete' for i in range(i1, i2)
        ]
        return BuildCheck('omission', missing, missing[0][0])
    return BuildCheck('wrong', [], None)
