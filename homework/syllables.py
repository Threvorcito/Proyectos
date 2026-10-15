"""Spanish syllabification (pure Python, no Django dependencies)."""
import re
from typing import NamedTuple

WORD = re.compile(r'[^\W\d_]+')

VOWELS = frozenset('aeiouáéíóúü')
STRONG = frozenset('aeoáéíóú')  # accented i/u act as strong: rí-o, pa-ís
INSEPARABLE = frozenset(
    {'pl', 'pr', 'bl', 'br', 'fl', 'fr', 'cl', 'cr', 'gl', 'gr', 'kl', 'kr', 'tr', 'dr', 'tl'}
)
_DIGRAPHS = frozenset({'ch', 'll', 'rr'})


class Unit(NamedTuple):
    text: str
    is_vowel: bool


def _lower(char):
    return char.lower() if len(char.lower()) == 1 else char


def word_units(word):
    """Split a word into vowel and consonant units, keeping the original text."""
    low = [_lower(c) for c in word]
    units = []
    i = 0
    while i < len(word):
        c = low[i]
        nxt = low[i + 1] if i + 1 < len(word) else ''
        if c + nxt in _DIGRAPHS or (c in 'qg' and nxt == 'u' and i + 2 < len(word) and low[i + 2] in 'eéií'):
            units.append(Unit(word[i:i + 2], False))
            i += 2
            continue
        if c == 'y':
            is_vowel = not nxt or nxt not in VOWELS
        else:
            is_vowel = c in VOWELS
        units.append(Unit(word[i], is_vowel))
        i += 1
    return units


def _nuclei(units):
    """Return (start, end) unit ranges of each vowel nucleus."""
    nuclei = []
    i = 0
    while i < len(units):
        if not units[i].is_vowel:
            i += 1
            continue
        start = i
        i += 1
        while i < len(units) and units[i].is_vowel:
            if _lower(units[i - 1].text) in STRONG and _lower(units[i].text) in STRONG:
                break
            i += 1
        nuclei.append((start, i))
    return nuclei


def _boundary(units, end_a, start_b):
    """Index where the next syllable begins, given the consonants between two nuclei."""
    n = start_b - end_a
    if n <= 1:
        return end_a if n == 1 else start_b
    cons = [_lower(u.text) for u in units[end_a:start_b]]
    if n == 2:
        return end_a if ''.join(cons) in INSEPARABLE else end_a + 1
    if n == 3:
        return end_a + 1 if ''.join(cons[1:]) in INSEPARABLE else end_a + 2
    return end_a + 2


def syllable_units(word):
    units = word_units(word)
    nuclei = _nuclei(units)
    if not nuclei:
        return [units] if units else []
    cuts = [_boundary(units, a[1], b[0]) for a, b in zip(nuclei, nuclei[1:])]
    edges = [0, *cuts, len(units)]
    return [units[s:e] for s, e in zip(edges, edges[1:])]


def split_syllables(word):
    return [''.join(u.text for u in syl) for syl in syllable_units(word)]
