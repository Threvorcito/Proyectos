"""Dictado step: teacher authoring, the child's one-item-at-a-time screen, resume and the teacher preview."""
import json
import re

from django.urls import reverse

from .models import TaskAssignment, TaskStep
from .services import append_step
from .tests_teacher import TeacherTaskTestCase
from .views_student import step_context

WORDS = ['mesa', 'mamá', 'cama', 'lima', 'humo']
SENTENCES = ['Mi mamá me ama.', 'Amo a mi mamá.']
PAYLOAD = {'letter': 'm', 'words': WORDS, 'sentences': SENTENCES}


class DictadoAuthoringTests(TeacherTaskTestCase):
    def setUp(self):
        super().setUp()
        self.task = self._task(title='Dictado de la m')

    def create_url(self):
        return reverse('homework:step_create', args=[self.task.pk, 'dictado'])

    def test_teacher_creates_dictado(self):
        response = self.client.post(self.create_url(), {
            'letter': ' M ',
            'words': 'mesa\n mamá \n\ncama\nlima\nhumo\n',
            'sentences': 'Mi mamá me ama.\nAmo a mi mamá.',
        })
        self.assertRedirects(response, reverse('homework:task_detail', args=[self.task.pk]))
        step = self.task.steps.get()
        self.assertEqual(step.step_type, TaskStep.StepType.DICTADO)
        self.assertEqual(step.payload, PAYLOAD)

    def test_teacher_dictado_rejects_four_words(self):
        response = self.client.post(self.create_url(), {
            'letter': 'm', 'words': 'mesa\nmamá\ncama\nlima', 'sentences': '\n'.join(SENTENCES),
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dictado: escribe exactamente 5 palabras distintas.')
        self.assertFalse(self.task.steps.exists())

    def test_teacher_edit_form_starts_with_lines(self):
        step = append_step(self.task, 'dictado', dict(PAYLOAD))
        response = self.client.get(reverse('homework:step_update', args=[self.task.pk, step.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['words'], '\n'.join(WORDS))
        self.assertEqual(response.context['form'].initial['sentences'], '\n'.join(SENTENCES))

    def test_dictado_in_step_type_menu(self):
        response = self.client.get(reverse('homework:task_detail', args=[self.task.pk]))
        self.assertIn(('dictado', 'Dictado'), response.context['step_types'])

    def test_task_detail_summarizes_dictado(self):
        append_step(self.task, 'dictado', dict(PAYLOAD))
        response = self.client.get(reverse('homework:task_detail', args=[self.task.pk]))
        [(_step, summary)] = response.context['steps']
        self.assertIn('m', summary)
        self.assertIn('mesa', summary)

    def test_preview_renders_dictado(self):
        append_step(self.task, 'dictado', dict(PAYLOAD))
        response = self.client.get(reverse('homework:task_preview', args=[self.task.pk]))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(len(re.findall(r'data-dictado-item="\d"', html)), 7)
        # The teacher sees what each item asks for; the child page never does.
        for text in [*WORDS, *SENTENCES]:
            self.assertIn(text, html)
        # Each item carries its own target for the preview's local check.
        self.assertEqual(len(re.findall(r'id="build-units-\d+-\d"', html)), 7)


class DictadoStudentTests(TeacherTaskTestCase):
    def setUp(self):
        super().setUp()
        self.task = self._task(title='Dictado de la m')
        self.step = append_step(self.task, 'dictado', dict(PAYLOAD))
        self.assignment = TaskAssignment.objects.create(task=self.task, student=self.ana)
        self.client.login(username='ana', password='x')

    def step_url(self, name='student_step'):
        return reverse(f'homework:{name}', args=[self.assignment.pk, self.step.order])

    def answer(self, item_index, tiles):
        body = {'item_index': item_index, 'tiles': tiles}
        return self.client.post(self.step_url('step_answer'), data=json.dumps(body), content_type='application/json')

    def test_step_context_items(self):
        context = step_context(self.step)['dictado']
        self.assertEqual(context['letter'], 'm')
        self.assertEqual([item['index'] for item in context['items']], list(range(7)))
        self.assertEqual(context['items'][0]['unit'], 'letter')
        self.assertEqual(context['items'][0]['say'], 'mesa')
        self.assertTrue({'m', 'e', 's', 'a'} <= set(context['items'][0]['tiles']))
        self.assertEqual(context['items'][5]['unit'], 'word')
        self.assertTrue({'Mi', 'mamá', 'me', 'ama'} <= set(context['items'][5]['tiles']))
        # Seeded per item: a reload never reshuffles.
        self.assertEqual(step_context(self.step)['dictado'], context)
        self.assertNotIn('preview_units', context['items'][0])

    def test_student_step_renders_listen_not_text(self):
        response = self.client.get(self.step_url())
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertContains(response, 'Escucha y arma lo que oyes con las fichas.')
        for word in WORDS:
            self.assertEqual(html.count(f'data-speak-text="{word}"'), 1)
        # "mesa" and "humo" are only words (never sentence tiles): they appear nowhere but in the audio attribute.
        for word in ('mesa', 'humo'):
            self.assertEqual(html.count(word), 1, word)
        self.assertNotIn('data-build-units', html)
        # One item at a time: only the first is visible.
        visible = re.findall(r'<div class="task-dictado__item[^"]*" data-dictado-item="(\d)"(?! hidden)', html)
        self.assertEqual(visible, ['0'])

    def test_student_resumes_dictado(self):
        for index, tiles in enumerate([['m', 'e', 's', 'a'], ['m', 'a', 'm', 'á'], ['c', 'a', 'm', 'a']]):
            self.assertEqual(self.answer(index, tiles).json()['status'], 'correct')
        response = self.client.get(self.step_url())
        self.assertEqual(response.context['done_items'], {0, 1, 2})
        html = response.content.decode()
        visible = re.findall(r'<div class="task-dictado__item[^"]*" data-dictado-item="(\d)"(?! hidden)', html)
        self.assertEqual(visible, ['3'])
        self.assertIn('data-dictado-item="0" hidden', html)
        self.assertEqual(html.count('task-dictado__item is-done'), 3)

    def test_each_item_posts_its_own_index(self):
        html = self.client.get(self.step_url()).content.decode()
        for index in range(7):
            self.assertIn(f'data-build-item="{index}"', html)
