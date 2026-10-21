"""Per-letter FAS lesson content bank (m to d), reviewable and editable by the teacher.

Every text for a letter uses only vowels and consonants up to and including that letter
in the official sequence (``fas_sequence.known_letters``); ``tests_fas_content`` checks it.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class LetterLesson:
    letter: str
    words: tuple  # exactly 6; the first 5 feed the dictado
    sentences: tuple  # exactly 2; the first one is built from word tiles
    build_word: str
    reading: str


def _lesson(letter, words, sentences, build_word, reading):
    return letter, LetterLesson(letter, tuple(words), tuple(sentences), build_word, reading)


LESSONS = dict((
    _lesson(
        'm', ('mamá', 'mimo', 'ama', 'Memo', 'mío', 'mima'),
        ('Mamá me ama.', 'Amo a mi mamá.'),
        'mamá',
        'Mamá me mima. Memo ama a mamá. Mamá ama a Memo.',
    ),
    _lesson(
        'p', ('papá', 'mapa', 'pipa', 'Pepe', 'puma', 'pomo'),
        ('Papá ama a Pepe.', 'Mi mamá ama a papá.'),
        'pipa',
        'Pepe ama a papá. Papá mima a Pepe. Mi mamá ama a papá.',
    ),
    _lesson(
        'b', ('bebé', 'boa', 'bambú', 'bombo', 'bomba', 'Bobi'),
        ('Mamá mima a mi bebé.', 'Papá ama a Bobi.'),
        'bebé',
        'Mi bebé bebe. Bobi mima a mi bebé. Papá ama a Bobi.',
    ),
    _lesson(
        'v', ('uva', 'ave', 'pavo', 'Eva', 'mueve', 'Vivi'),
        ('Eva vio a mi pavo.', 'Vivi ama a Eva.'),
        'pavo',
        'Eva vio a mi pavo. Mi pavo vio a Eva. Eva mima a mi pavo.',
    ),
    _lesson(
        's', ('sopa', 'mesa', 'oso', 'sapo', 'vaso', 'beso'),
        ('Mi oso es suave.', 'Mamá besa a su bebé.'),
        'mesa',
        'Mi oso es suave. Mamá me besa. Papá me pasa su vaso.',
    ),
    _lesson(
        'c', ('casa', 'coco', 'vaca', 'cama', 'boca', 'peces'),
        ('Papá come coco.', 'Mi cama es suave.'),
        'casa',
        'Papá come coco. Mamá come sopa. Mi bebé come papas.',
    ),
    _lesson(
        'z', ('pez', 'maíz', 'voz', 'cabeza', 'pozo', 'Zoe'),
        ('Mi vaca come maíz.', 'Zoe ve su pez.'),
        'cabeza',
        'Zoe ve su pez. Su pez come maíz. Zoe besa a su pez.',
    ),
    _lesson(
        'l', ('lobo', 'sol', 'ala', 'vela', 'pelo', 'luz'),
        ('La paloma vuela.', 'El sol sale.'),
        'paloma',
        'El sol sale. La paloma vuela sola. Lola la ve.',
    ),
    _lesson(
        'n', ('luna', 'mano', 'nube', 'pan', 'cuna', 'mono'),
        ('La luna sale.', 'Nina come un pan.'),
        'banana',
        'La luna sale. Una nube pasa. Nina ve la luna.',
    ),
    _lesson(
        'f', ('foca', 'sofá', 'café', 'foco', 'fila', 'Felipe'),
        ('Felipe ve una foca.', 'Papá bebe café.'),
        'foca',
        'Felipe ve una foca. La foca es feliz. Felipe es feliz.',
    ),
    _lesson(
        't', ('pato', 'moto', 'taza', 'tomate', 'pelota', 'tapa'),
        ('El pato come tomate.', 'Tito tiene una moto.'),
        'pelota',
        'El pato come tomate. Tito ve al pato. El pato es feliz.',
    ),
    _lesson(
        'd', ('dado', 'dedo', 'nido', 'codo', 'día', 'moneda'),
        ('Daniel tiene un dado.', 'El ave está en su nido.'),
        'moneda',
        'Daniel tiene un dado. Daniel lo lanza. El dado cae.',
    ),
))


def lesson_for(letter: str):
    """The lesson for ``letter``, or None when the bank has no content for it."""
    return LESSONS.get(letter)
