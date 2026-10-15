import json
import re

from django.test import SimpleTestCase
from django.urls import reverse

from homework.forms import ArmaStepForm, ContestaStepForm
from homework.models import OmissionEvent, StepResult, TaskAssignment
from homework.payloads import BuildTarget, build_target
from homework.services import append_step
from homework.tests_student import StudentTaskTestCase

from homework.writing import BUILD_MAX_UNITS, build_tiles, check_build, split_units


class WritingTests(SimpleTestCase):
    def test_split_units(self):
        self.assertEqual(split_units('carro', 'letter'), ['c', 'a', 'rr', 'o'])
        self.assertEqual(split_units('mariposa', 'syllable'), ['ma', 'ri', 'po', 'sa'])
        self.assertEqual(split_units('El gato come.', 'word'), ['El', 'gato', 'come'])
        with self.assertRaises(ValueError):
            split_units('el gato', 'syllable')
        with self.assertRaises(ValueError):
            split_units('el gato', 'letter')

    def test_build_tiles_counts_and_distractors(self):
        tiles = build_tiles(['ca', 'sa'], 'syllable', seed=1)
        self.assertEqual(len(tiles), 4)
        self.assertTrue({'ca', 'sa'} <= set(tiles))
        tiles = build_tiles(['m', 'a', 'm', 'á'], 'letter', seed=1)
        self.assertEqual(len(tiles), 7)
        self.assertIn('n', tiles)

    def test_confusable_syllable_swap(self):
        self.assertIn('da', build_tiles(['ba', 'sa'], 'syllable', seed=3))

    def test_word_fallback_pool(self):
        tiles = build_tiles(['sol'], 'word', seed=2)
        self.assertEqual(len(tiles), 3)

    def test_build_tiles_deterministic(self):
        a = build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=7)
        self.assertEqual(a, build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=7))
        self.assertTrue(any(
            build_tiles(['ma', 'ri', 'po', 'sa'], 'syllable', seed=s) != a for s in range(20)
        ))

    def test_distractors_never_equal_targets(self):
        for seed in range(20):
            tiles = build_tiles(['b', 'd', 'a'], 'letter', seed=seed)
            self.assertEqual(len(tiles), 6)
            self.assertEqual(sorted(t for t in tiles if t in ('b', 'd', 'a')), ['a', 'b', 'd'])
            self.assertEqual(len({t.casefold() for t in tiles}), 6)

    def test_check_build(self):
        self.assertEqual(check_build(['ca', 'sa'], ['Ca', 'sa']).status, 'correct')
        c = check_build(['ma', 'ri', 'po', 'sa'], ['ma', 'po', 'sa'])
        self.assertEqual((c.status, c.missing, c.hole_index), ('omission', [(1, 'ri')], 1))
        self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a']).missing, [(2, 't'), (3, 'o')])
        self.assertEqual(check_build(['g', 'a', 't', 'o'], ['g', 'a', 'd', 'o']).status, 'wrong')
        self.assertEqual(check_build(['ca', 'sa'], ['sa', 'ca']).status, 'wrong')

    def test_wrong_has_no_missing(self):
        c = check_build(['ca', 'sa'], ['sa', 'ca'])
        self.assertEqual((c.missing, c.hole_index), ([], None))

    def test_missing_unit_is_capped_to_model_limit(self):
        c = check_build(['x' * 50, 'a'], ['a'])
        self.assertEqual(c.status, 'omission')
        self.assertEqual(len(c.missing[0][1]), 30)


class BuildSpecTests(SimpleTestCase):
    def test_build_target_reads_blank_or_whole_text(self):
        self.assertEqual(
            build_target('arma', {'text': 'El [gato] come.', 'unit': 'word'}),
            BuildTarget(before='El ', text='gato', after=' come.', unit='word'),
        )
        self.assertEqual(build_target('arma', {'text': 'mariposa', 'unit': 'syllable'}).text, 'mariposa')

    def test_contesta_build_unit_depends_on_spaces(self):
        base = {'question': 'Q', 'kind': 'build'}
        self.assertEqual(build_target('contesta', {**base, 'answer': 'casa'}).unit, 'syllable')
        self.assertEqual(build_target('contesta', {**base, 'answer': 'la casa'}).unit, 'word')

    def test_syllable_tiles_never_use_single_letter_distractors(self):
        for seed in range(30):
            tiles = build_tiles(['ma', 'ri'], 'syllable', seed=seed)
            self.assertTrue(all(len(t) >= 2 for t in tiles), tiles)


class ArmaPlayerTestCase(StudentTaskTestCase):
    def _arma(self, payload, step_type='arma'):
        task = self._task(title='Armar')
        step = append_step(task, step_type, payload)
        assignment = TaskAssignment.objects.create(task=task, student=self.ana)
        return step, assignment

    def answer(self, step, assignment, tiles):
        return self.client.post(
            self.step_url(step.order, 'step_answer', assignment),
            data=json.dumps({'item_index': 0, 'tiles': tiles}),
            content_type='application/json',
        )


class ArmaEvaluationTests(ArmaPlayerTestCase):
    def test_arma_omission_records_event_and_hint(self):
        step, assignment = self._arma({'text': 'mariposa', 'unit': 'syllable'})
        body = self.answer(step, assignment, ['ma', 'po', 'sa']).json()
        self.assertEqual(body['status'], 'try_again')
        self.assertEqual(body['hint'], {'say': 'ri', 'hole_index': 1, 'kind': 'omission'})
        event = OmissionEvent.objects.get()
        self.assertEqual((event.target, event.missing_unit, event.position), ('mariposa', 'ri', 1))
        self.assertEqual(event.step, step)

    def test_letter_omission_hint_is_phoneme(self):
        step, assignment = self._arma({'text': 'gato', 'unit': 'letter'})
        body = self.answer(step, assignment, ['g', 'a', 'o']).json()
        self.assertEqual(body['hint'], {'say': 'to', 'hole_index': 2, 'kind': 'omission'})
        self.assertEqual(OmissionEvent.objects.get().missing_unit, 't')

    def test_continuant_letter_hint_is_elongated_never_the_letter_name(self):
        step, assignment = self._arma({'text': 'mesa', 'unit': 'letter'})
        body = self.answer(step, assignment, ['e', 's', 'a']).json()
        self.assertEqual(body['hint']['say'], 'mmm')

    def test_blank_sentence_checks_only_blank(self):
        step, assignment = self._arma({'text': 'El [gato] come.', 'unit': 'word'})
        body = self.answer(step, assignment, ['gato']).json()
        self.assertEqual(body['status'], 'correct')
        self.assertTrue(body['step_done'])
        self.assertEqual(StepResult.objects.get().answer, 'gato')

    def test_second_failure_models_full_text(self):
        step, assignment = self._arma({'text': 'El [gato] come.', 'unit': 'word'})
        first = self.answer(step, assignment, ['perro']).json()
        self.assertEqual(first['hint'], {'say': 'gato', 'hole_index': None, 'kind': 'try_again'})
        self.assertFalse(OmissionEvent.objects.exists())
        second = self.answer(step, assignment, ['perro']).json()
        self.assertEqual((second['status'], second['model_answer']), ('modeled', 'El gato come.'))

    def test_word_answer_text_is_space_joined_and_letters_are_not(self):
        step, assignment = self._arma({'text': 'el gato', 'unit': 'word'})
        self.answer(step, assignment, ['el', 'gato'])
        self.assertEqual(StepResult.objects.get().answer, 'el gato')
        step, assignment = self._arma({'text': 'casa', 'unit': 'syllable'})
        self.answer(step, assignment, ['ca', 'sa'])
        self.assertEqual(StepResult.objects.get(step=step).answer, 'casa')

    def test_contesta_build_uses_word_tiles(self):
        step, assignment = self._arma(
            {'question': '¿Dónde vive?', 'kind': 'build', 'options': [], 'answer': 'la casa'}, 'contesta'
        )
        body = self.answer(step, assignment, ['la']).json()
        self.assertEqual(body['hint'], {'say': 'casa', 'hole_index': 1, 'kind': 'omission'})
        self.assertEqual(self.answer(step, assignment, ['la', 'casa']).json()['status'], 'correct')

    def test_bad_tiles_payload_400(self):
        step, assignment = self._arma({'text': 'casa', 'unit': 'syllable'})
        for tiles in ('ma', [], [1], ['ca'] * (2 * BUILD_MAX_UNITS + 1), None):
            response = self.answer(step, assignment, tiles)
            self.assertEqual(response.status_code, 400, tiles)
        self.assertFalse(StepResult.objects.filter(attempts__gt=0).exists())


class ArmaFormTests(StudentTaskTestCase):
    def _form(self, **data):
        return ArmaStepForm(data, task=self.task)

    def test_arma_form_rejects_multiword_letter_target(self):
        for unit in ('letter', 'syllable'):
            form = self._form(text='el gato', unit=unit)
            self.assertFalse(form.is_valid())
            self.assertIn('Para letras o sílabas usa una sola palabra.', form.non_field_errors())
        self.assertTrue(self._form(text='el [gato]', unit='word').is_valid())
        self.assertFalse(self._form(text='el [gato] [come]', unit='word').is_valid())

    def test_arma_form_enforces_unit_limit(self):
        long_text = ' '.join(['sol'] * (BUILD_MAX_UNITS + 1))
        self.assertFalse(self._form(text=long_text, unit='word').is_valid())
        self.assertTrue(self._form(text=' '.join(['sol'] * BUILD_MAX_UNITS), unit='word').is_valid())

    def test_contesta_build_form_needs_no_options_and_checks_limit(self):
        data = {'question': 'Q', 'kind': 'build', 'options': '', 'answer': 'la casa'}
        form = ContestaStepForm(data, task=self.task)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.to_payload()['options'], [])
        too_long = ContestaStepForm({**data, 'answer': ' '.join(['sol'] * (BUILD_MAX_UNITS + 1))}, task=self.task)
        self.assertFalse(too_long.is_valid())
        choice = ContestaStepForm({**data, 'kind': 'choice'}, task=self.task)
        self.assertFalse(choice.is_valid())

    def test_arma_step_created_through_view(self):
        self.client.login(username='maestra', password='x')
        response = self.client.post(
            reverse('homework:step_create', args=[self.task.pk, 'arma']), {'text': 'mariposa', 'unit': 'syllable'}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.task.steps.get(step_type='arma').payload, {'text': 'mariposa', 'unit': 'syllable'})


class TilePageTests(ArmaPlayerTestCase):
    def _page(self, payload, step_type='arma'):
        step, assignment = self._arma(payload, step_type)
        return self.client.get(self.step_url(step.order, assignment=assignment)).content.decode()

    def test_tiles_rendered_include_distractors(self):
        html = self._page({'text': 'casa', 'unit': 'syllable'})
        self.assertEqual(html.count('data-tile='), 4)
        self.assertIn('data-build-check', html)
        self.assertIn('tiles.js', html)

    def test_blank_sentence_shows_context_around_the_hole(self):
        html = self._page({'text': 'El [gato] come.', 'unit': 'word'})
        self.assertEqual(html.count('data-tile='), 3)
        self.assertIn('data-build-before', html)
        self.assertIn('come.', html)

    def test_child_page_does_not_leak_the_target_units(self):
        self.assertNotIn('data-build-units', self._page({'text': 'casa', 'unit': 'syllable'}))

    def test_tile_order_is_stable_between_loads(self):
        step, assignment = self._arma({'text': 'mariposa', 'unit': 'syllable'})
        url = self.step_url(step.order, assignment=assignment)
        first, second = (self.client.get(url).content.decode() for _ in range(2))
        tiles = lambda html: re.findall(r'data-tile="([^"]*)"', html)
        self.assertEqual(tiles(first), tiles(second))

    def test_contesta_build_page_shows_tiles_not_options(self):
        html = self._page({'question': '¿Dónde vive?', 'kind': 'build', 'options': [], 'answer': 'la casa'}, 'contesta')
        self.assertIn('data-tile=', html)
        self.assertNotIn('data-task-choice', html)

    def test_preview_renders_tiles_with_units_for_the_teacher_only(self):
        self.client.login(username='maestra', password='x')
        task = self._task(title='Prev')
        append_step(task, 'arma', {'text': 'casa', 'unit': 'syllable'})
        html = self.client.get(reverse('homework:task_preview', args=[task.pk])).content.decode()
        self.assertEqual(html.count('data-tile='), 4)
        self.assertIn('data-build-units', html)
