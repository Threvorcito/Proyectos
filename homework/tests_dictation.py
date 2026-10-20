import json

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from django.utils import timezone

from .dictation import BreakPoint, Criteria, item_target, letter_ok, score
from .evaluation import InvalidAnswer
from .models import StepResult, TaskAssignment
from .payloads import clean_payload
from .services import append_step, mark_item_done
from .tests_student import StudentTaskTestCase

WORDS = ['mesa', 'mamá', 'cama', 'lima', 'humo']
SENTENCES = ['Mi mamá me ama.', 'Amo a mi mamá.']
PAYLOAD = {'letter': 'm', 'words': WORDS, 'sentences': SENTENCES}


def _result(answer='', first_try_correct=True, modeled=False, completed=True):
    return StepResult(
        first_answer=answer,
        first_try_correct=first_try_correct,
        modeled=modeled,
        completed_at=timezone.now() if completed else None,
    )


def _results(**overrides):
    """All 7 items done right on the first try; ``overrides`` maps item index to a replacement result."""
    results = {i: _result(word) for i, word in enumerate(WORDS)}
    results.update({5: _result(SENTENCES[0]), 6: _result(SENTENCES[1])})
    results.update({int(key[1:]): value for key, value in overrides.items()})
    return results


class DictadoPayloadTests(SimpleTestCase):
    def test_clean_dictado_normalizes(self):
        data = {'letter': ' M ', 'words': [f' {w} ' for w in WORDS], 'sentences': [f'{s} ' for s in SENTENCES]}
        self.assertEqual(clean_payload('dictado', data), PAYLOAD)

    def test_clean_dictado_rejects(self):
        cases = {
            'four words': {'words': WORDS[:4]},
            'six words': {'words': WORDS + ['mono']},
            'duplicate words': {'words': WORDS[:4] + ['mesa']},
            'word with a space': {'words': WORDS[:4] + ['la mesa']},
            'word without the letter': {'words': WORDS[:4] + ['sol']},
            'one sentence': {'sentences': SENTENCES[:1]},
            'one-word sentence': {'sentences': [SENTENCES[0], 'Mamá.']},
            'letter with digits': {'letter': 'm1'},
            'empty letter': {'letter': '  '},
        }
        for name, override in cases.items():
            with self.subTest(name), self.assertRaises(ValidationError):
                clean_payload('dictado', {**PAYLOAD, **override})

    def test_clean_dictado_accepts_digraph_letter(self):
        data = {'letter': 'LL', 'words': ['calle', 'llave', 'pollo', 'silla', 'lluvia'], 'sentences': SENTENCES}
        self.assertEqual(clean_payload('dictado', data)['letter'], 'll')


class DictadoItemTests(SimpleTestCase):
    def test_item_target(self):
        first = item_target(PAYLOAD, 0)
        self.assertEqual((first.unit, first.text), ('letter', 'mesa'))
        last = item_target(PAYLOAD, 6)
        self.assertEqual((last.unit, last.text), ('word', 'Amo a mi mamá.'))
        for index in (7, -1):
            with self.subTest(index), self.assertRaises(IndexError):
                item_target(PAYLOAD, index)

    def test_letter_ok(self):
        self.assertTrue(letter_ok('mesa', 'mesa', 'm'))
        self.assertFalse(letter_ok('mesa', 'nesa', 'm'))
        self.assertTrue(letter_ok('mesa', 'msa', 'm'))
        self.assertTrue(letter_ok('Mamá', 'mamá', 'm'))
        self.assertFalse(letter_ok('calle', 'cale', 'll'))
        self.assertTrue(letter_ok('calle', 'calle', 'll'))
        self.assertFalse(letter_ok('mesa', '', 'm'))


class DictadoScoreTests(SimpleTestCase):
    def test_score_incomplete(self):
        results = _results()
        del results[6]
        self.assertEqual(score(PAYLOAD, results), (BreakPoint.INCOMPLETE, None))
        self.assertEqual(score(PAYLOAD, _results(i6=_result(completed=False))), (BreakPoint.INCOMPLETE, None))

    def test_score_sound_letter(self):
        results = _results(i0=_result('nesa', False), i1=_result('namá', False))
        self.assertEqual(score(PAYLOAD, results)[0], BreakPoint.SOUND_LETTER)

    def test_score_words(self):
        results = _results(i2=_result('cma', False), i3=_result('lma', False))
        self.assertEqual(score(PAYLOAD, results), (BreakPoint.WORDS, Criteria(True, False, True)))

    def test_score_sentences(self):
        results = _results(i5=_result('Mi me ama', False, modeled=True))
        self.assertEqual(score(PAYLOAD, results), (BreakPoint.SENTENCES, Criteria(True, True, False)))

    def test_score_none(self):
        self.assertEqual(score(PAYLOAD, _results()), (BreakPoint.NONE, Criteria(True, True, True)))


class DictadoStepTests(StudentTaskTestCase):
    def setUp(self):
        super().setUp()
        self.dictado_task = self._task(title='Dictado de la m')
        self.dictado = append_step(self.dictado_task, 'dictado', dict(PAYLOAD))
        self.dictado_assignment = TaskAssignment.objects.create(task=self.dictado_task, student=self.ana)

    def answer(self, item_index, tiles):
        url = self.step_url(1, 'step_answer', self.dictado_assignment)
        body = {'item_index': item_index, 'tiles': tiles}
        return self.client.post(url, data=json.dumps(body), content_type='application/json').json()

    def test_item_count_is_seven(self):
        self.assertEqual(self.dictado.item_count, 7)

    def test_submit_dictado_word_and_sentence(self):
        self.assertEqual(self.answer(0, ['m', 'e', 's', 'a'])['status'], 'correct')
        self.assertEqual(self.answer(5, ['Amo', 'mi'])['status'], 'try_again')
        self.assertEqual(self.answer(5, ['Amo', 'mi'])['status'], 'modeled')
        with self.assertRaises(InvalidAnswer):
            mark_item_done(self.dictado_assignment, self.dictado, 1)

    def test_submit_dictado_sentence_punctuation(self):
        self.assertEqual(self.answer(5, ['Mi', 'mamá', 'me', 'ama'])['status'], 'correct')
