import re

from django.urls import reverse

from .models import StepResult, TaskAssignment
from .services import append_step
from .tests_student import StudentTaskTestCase

EXAMPLE = '2 + 1 = ?\nCuento 2 y sumo 1\n2 + 1 = 3'

EXERCISES = [
    {'prompt': '3 + 1 = ?', 'answer': '4', 'options': ['4', '5', '3']},
    {'prompt': '2 + 2 = ?', 'answer': '4', 'options': ['3', '4', '5']},
]


def form_data(rows, example=EXAMPLE, total=None):
    data = {
        'example_steps': example,
        'exercises-TOTAL_FORMS': str(total if total is not None else len(rows)),
        'exercises-INITIAL_FORMS': '0',
        'exercises-MIN_NUM_FORMS': '1',
        'exercises-MAX_NUM_FORMS': '5',
    }
    for i, (prompt, answer, distractors) in enumerate(rows):
        data[f'exercises-{i}-prompt'] = prompt
        data[f'exercises-{i}-answer'] = answer
        data[f'exercises-{i}-distractors'] = distractors
    return data


class EjemploFormTests(StudentTaskTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(username='maestra', password='x')

    def url(self, task):
        return reverse('homework:step_create', args=[task.pk, 'ejemplo'])

    def test_formset_builds_payload(self):
        task = self._task(title='Triángulos')
        self.client.post(self.url(task), form_data([('3 + 1 = ?', '4', '5, 3')]))
        step = task.steps.get()
        self.assertEqual(step.payload['example_steps'], ['2 + 1 = ?', 'Cuento 2 y sumo 1', '2 + 1 = 3'])
        self.assertEqual(step.payload['exercises'], [{'prompt': '3 + 1 = ?', 'answer': '4', 'options': ['4', '5', '3']}])

    def test_formset_requires_one_exercise(self):
        task = self._task(title='Vacía')
        response = self.client.post(self.url(task), form_data([('', '', '')], total=3))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.steps.count(), 0)

    def test_blank_extra_exercises_are_ignored(self):
        task = self._task(title='Extras')
        rows = [('3 + 1 = ?', '4', '5'), ('', '', ''), ('', '', '')]
        self.client.post(self.url(task), form_data(rows))
        self.assertEqual(len(task.steps.get().payload['exercises']), 1)

    def test_too_many_distractors_rejected(self):
        task = self._task(title='Muchas')
        response = self.client.post(self.url(task), form_data([('3 + 1 = ?', '4', '5, 6, 7, 8')]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.steps.count(), 0)

    def test_distractor_equal_to_answer_is_not_a_second_option(self):
        task = self._task(title='Igual')
        response = self.client.post(self.url(task), form_data([('3 + 1 = ?', '4', '4')]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.steps.count(), 0)

    def test_edit_form_is_prefilled(self):
        step = append_step(self.task, 'ejemplo', {'example_steps': ['a', 'b'], 'exercises': EXERCISES})
        html = self.client.get(reverse('homework:step_update', args=[self.task.pk, step.pk])).content.decode()
        self.assertIn('3 + 1 = ?', html)
        self.assertIn('5, 3', html)

    def test_task_detail_summarises_example(self):
        append_step(self.task, 'ejemplo', {'example_steps': ['Triángulo de 5 cm'], 'exercises': EXERCISES})
        self.assertContains(self.client.get(reverse('homework:task_detail', args=[self.task.pk])), 'Triángulo de 5 cm')


class EjemploPlayTests(StudentTaskTestCase):
    def setUp(self):
        super().setUp()
        self.task = self._task(title='Sumas')
        self.step = append_step(self.task, 'ejemplo', {'example_steps': EXAMPLE.split('\n'), 'exercises': EXERCISES})
        self.assignment = TaskAssignment.objects.create(task=self.task, student=self.ana)

    def answer(self, index, choice):
        return self.post(1, 'step_answer', {'item_index': index, 'choice': choice})

    def test_exercise_items_close_step(self):
        first = self.answer(0, 0).json()
        self.assertEqual(first['status'], 'correct')
        self.assertFalse(first['step_done'])
        second = self.answer(1, 1).json()
        self.assertEqual(second['status'], 'correct')
        self.assertTrue(second['step_done'])

    def test_exercise_wrong_twice_models_answer(self):
        self.assertEqual(self.answer(0, 1).json()['status'], 'try_again')
        outcome = self.answer(0, 2).json()
        self.assertEqual(outcome['status'], 'modeled')
        self.assertEqual(outcome['model_answer'], '4')
        self.assertEqual(StepResult.objects.get(item_index=0).answer, '3')

    def test_wrong_answer_hint_reads_the_prompt(self):
        hint = self.answer(0, 1).json()['hint']
        self.assertEqual(hint, {'say': '3 + 1 = ?', 'hole_index': None, 'kind': 'try_again'})

    def test_choice_out_of_range_is_rejected(self):
        self.assertEqual(self.answer(0, 3).status_code, 400)

    def test_exercise_index_out_of_range_is_rejected(self):
        self.assertEqual(self.answer(2, 0).status_code, 400)

    def test_rendered_option_buttons_use_stored_indexes(self):
        html = self.client.get(self.step_url(1)).content.decode()
        pairs = re.findall(r'<button[^>]*data-task-choice="(\d+)"[^>]*>\s*([^<]+?)\s*</button>', html)
        self.assertEqual(len(pairs), 6)
        for exercise, rendered in zip(EXERCISES, (pairs[:3], pairs[3:])):
            self.assertEqual({(int(i), text) for i, text in rendered}, set(enumerate(exercise['options'])))

    def test_option_order_is_stable_across_loads(self):
        first = self.client.get(self.step_url(1)).content.decode()
        second = self.client.get(self.step_url(1)).content.decode()
        pattern = r'data-task-choice="(\d+)"'
        self.assertEqual(re.findall(pattern, first), re.findall(pattern, second))

    def test_page_has_listen_buttons_decoding_and_no_answer_leak(self):
        html = self.client.get(self.step_url(1)).content.decode()
        self.assertIn('data-ejemplo', html)
        self.assertGreaterEqual(html.count('data-speak-text'), 3)
        self.assertIn('data-decodable', html)
        self.assertNotIn('correcta', html)

    def test_preview_marks_correct_option(self):
        self.client.login(username='maestra', password='x')
        html = self.client.get(reverse('homework:task_preview', args=[self.task.pk])).content.decode()
        self.assertEqual(html.count('✓ correcta'), 2)

    def test_reload_resumes_at_first_unfinished_exercise(self):
        self.answer(0, 0)
        html = self.client.get(self.step_url(1)).content.decode()
        self.assertIn('data-ejemplo-resume', html)

    def test_closed_exercise_reports_step_not_done_while_others_remain(self):
        self.answer(0, 0)
        again = self.answer(0, 0)
        self.assertEqual(again.status_code, 409)
        body = again.json()
        self.assertFalse(body['step_done'])
        self.assertIsNone(body['next_url'])

    def test_closed_last_exercise_reports_step_done(self):
        self.answer(0, 0)
        self.answer(1, 1)
        body = self.answer(1, 1).json()
        self.assertTrue(body['step_done'])
        self.assertTrue(body['next_url'])

    def test_page_has_walkthrough_hooks(self):
        html = self.client.get(self.step_url(1)).content.decode()
        for hook in ('data-ejemplo-next', 'data-ejemplo-practice', 'data-ejemplo-continue', 'data-ejemplo-line', 'data-exercise="1"'):
            self.assertIn(hook, html)
