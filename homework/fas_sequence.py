"""Official FAS phoneme presentation order (MINED, Educación Especial Tomo I, PDF p38).

Each grapheme appears once, at its first position in the tome: c only with s and z,
the consonant y only in the ñ group (the vowel-group y is skipped). x and w, which the
tome presents apart, are not part of this sequence.
"""

VOWELS = ('a', 'e', 'i', 'o', 'u')

GROUPS = (
    ('Aprestamiento: vocales cerradas y diptongos', ('i', 'u')),
    ('Aprestamiento: vocales abiertas', ('a', 'e', 'o')),
    ('Consonantes bilabiales', ('m', 'p', 'b', 'v')),
    ('Consonantes linguoalveolares, sílabas inversas y mixtas', ('s', 'c', 'z')),
    ('Consonantes linguoalveolares, sílabas directas dobles o complejas', ('l', 'n')),
    ('Consonantes labiodentales y linguodentales', ('f', 't', 'd')),
    ('Consonantes linguoalveolares (r, rr)', ('r', 'rr')),
    ('Consonantes linguopalatales', ('ñ', 'll', 'y', 'h', 'ch')),
    ('Consonantes linguoalveolares (k, q, g, j)', ('k', 'q', 'g', 'j')),
)

CONSONANTS = tuple(letter for _, letters in GROUPS for letter in letters if letter not in VOWELS)


def known_letters(letter: str) -> frozenset:
    """Vowels plus every consonant up to and including ``letter``; KeyError if not a consonant."""
    if letter not in CONSONANTS:
        raise KeyError(letter)
    return frozenset(VOWELS) | frozenset(CONSONANTS[:CONSONANTS.index(letter) + 1])
