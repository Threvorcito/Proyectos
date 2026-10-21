"""Official FAS letter sequence and the per-letter lesson content bank."""
from django.test import SimpleTestCase

from .fas_content import LESSONS, lesson_for
from .fas_sequence import CONSONANTS, GROUPS, VOWELS, known_letters
from .payloads import clean_payload
from .writing import _PLAIN, split_units

CONTENT_LETTERS = {'m', 'p', 'b', 'v', 's', 'c', 'z', 'l', 'n', 'f', 't', 'd'}


def _plain(unit):
    return unit.casefold().translate(_PLAIN)


def _units(text):
    for word in split_units(text, 'word'):
        for unit in split_units(word, 'letter'):
            yield _plain(unit)


class FasSequenceTests(SimpleTestCase):
    def test_sequence_order(self):
        self.assertEqual(CONSONANTS[:4], ('m', 'p', 'b', 'v'))
        self.assertLess(CONSONANTS.index('h'), CONSONANTS.index('ch'))
        self.assertEqual(len(CONSONANTS), len(set(CONSONANTS)))
        self.assertEqual(VOWELS, ('a', 'e', 'i', 'o', 'u'))
        grouped = tuple(letter for _, letters in GROUPS for letter in letters if letter not in VOWELS)
        self.assertEqual(grouped, CONSONANTS)
        self.assertIn('Aprestamiento', GROUPS[0][0])

    def test_known_letters(self):
        self.assertEqual(known_letters('m'), frozenset('aeioum'))
        self.assertNotIn('s', known_letters('v'))
        known_letters('r')
        with self.assertRaises(KeyError):
            known_letters('x')
        with self.assertRaises(KeyError):
            known_letters('a')


class FasContentTests(SimpleTestCase):
    def test_lessons_cover_m_to_d(self):
        self.assertEqual(set(LESSONS), CONTENT_LETTERS)
        self.assertIs(lesson_for('m'), LESSONS['m'])
        self.assertIsNone(lesson_for('r'))

    def test_lesson_shape(self):
        for letter, lesson in LESSONS.items():
            with self.subTest(letter=letter):
                self.assertEqual(lesson.letter, letter)
                self.assertEqual(len(lesson.words), 6)
                self.assertEqual(len(lesson.sentences), 2)

    def test_lessons_use_only_known_letters(self):
        for letter, lesson in LESSONS.items():
            known = known_letters(letter)
            texts = (*lesson.words, *lesson.sentences, lesson.build_word, lesson.reading)
            for text in texts:
                for unit in _units(text):
                    self.assertIn(
                        unit, known,
                        f'lesson «{letter}»: «{text}» uses «{unit}», not taught yet',
                    )

    def test_words_contain_letter(self):
        for letter, lesson in LESSONS.items():
            for word in (*lesson.words, lesson.build_word):
                self.assertIn(letter, list(_units(word)), f'lesson «{letter}»: «{word}» lacks the letter')

    def test_payloads_validate(self):
        for letter, lesson in LESSONS.items():
            with self.subTest(letter=letter):
                clean_payload('palabras', {'words': list(lesson.words)})
                clean_payload('arma', {'text': lesson.build_word, 'unit': 'syllable'})
                clean_payload('arma', {'text': lesson.sentences[0], 'unit': 'word'})
                clean_payload('lectura', {'text': lesson.reading})
                clean_payload('dictado', {
                    'letter': letter,
                    'words': list(lesson.words[:5]),
                    'sentences': list(lesson.sentences),
                })
