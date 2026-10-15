import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from readings.models import Reading

from .forms import STEP_FORMS, LecturaStepForm, PalabrasStepForm
from .models import Task, TaskAssignment
from .services import (
    TaskLocked,
    append_step,
    delete_step,
    duplicate_task,
    ensure_editable,
    move_step,
)
from .tests_teacher import TeacherTaskTestCase

LOCK_MESSAGE = 'Un alumno ya empezó esta tarea. Para cambiar los pasos, duplícala.'
GIF = (
    b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,'
    b'\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
)


class StepServiceTests(TeacherTaskTestCase):
    def _three(self):
        task = self._task()
        for n in range(3):
            append_step(task, 'mira', {'question': f'Pregunta {n}'}, image='tasks/x.gif')
        return task

    def test_append_steps_get_consecutive_orders(self):
        task = self._three()
        self.assertEqual(list(task.steps.values_list('order', flat=True)), [1, 2, 3])

    def test_move_step_up_swaps_orders(self):
        task = self._three()
        move_step(task.steps.get(order=2), 'up')
        self.assertEqual(
            [s.payload['question'] for s in task.steps.all()], ['Pregunta 1', 'Pregunta 0', 'Pregunta 2']
        )

    def test_move_step_down_swaps_orders(self):
        task = self._three()
        move_step(task.steps.get(order=2), 'down')
        self.assertEqual(
            [s.payload['question'] for s in task.steps.all()], ['Pregunta 0', 'Pregunta 2', 'Pregunta 1']
        )

    def test_move_first_step_up_is_noop(self):
        task = self._three()
        move_step(task.steps.get(order=1), 'up')
        self.assertEqual([s.payload['question'] for s in task.steps.all()], ['Pregunta 0', 'Pregunta 1', 'Pregunta 2'])

    def test_delete_step_renumbers(self):
        task = self._three()
        delete_step(task.steps.get(order=2))
        self.assertEqual(list(task.steps.values_list('order', flat=True)), [1, 2])
        self.assertEqual(task.steps.get(order=2).payload['question'], 'Pregunta 2')

    def test_duplicate_copies_steps_not_assignments(self):
        task = self._task()
        append_step(task, 'contesta', {'question': 'Q', 'kind': 'choice', 'options': ['a', 'b'], 'answer': 'a'})
        append_step(task, 'lectura', {'text': 'Un texto'})
        TaskAssignment.objects.create(task=task, student=self.ana, started_at=timezone.now())
        copy = duplicate_task(task)
        self.assertEqual(copy.title, 'Los animales (copia)')
        self.assertEqual(
            list(copy.steps.values_list('step_type', 'payload')), list(task.steps.values_list('step_type', 'payload'))
        )
        self.assertEqual(copy.assignments.count(), 0)
        self.assertFalse(copy.is_locked)
        self.assertIsNone(copy.due_date)

    def test_ensure_editable_raises_when_started(self):
        task = self._task()
        ensure_editable(task)
        TaskAssignment.objects.create(task=task, student=self.ana, started_at=timezone.now())
        with self.assertRaises(TaskLocked):
            ensure_editable(task)


class StepViewTests(TeacherTaskTestCase):
    def test_create_contesta_step_via_view_stores_payload(self):
        task = self._task()
        response = self.client.post(
            reverse('homework:step_create', args=[task.pk, 'contesta']),
            {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': 'zanahoria\npiedra', 'answer': 'zanahoria'},
        )
        self.assertRedirects(response, reverse('homework:task_detail', args=[task.pk]), fetch_redirect_response=False)
        self.assertEqual(
            task.steps.get().payload,
            {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': ['zanahoria', 'piedra'], 'answer': 'zanahoria'},
        )

    def test_contesta_answer_must_be_an_option(self):
        task = self._task()
        response = self.client.post(
            reverse('homework:step_create', args=[task.pk, 'contesta']),
            {'question': 'Q', 'kind': 'choice', 'options': 'a\nb', 'answer': 'z'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(task.steps.count(), 0)

    def test_mira_step_requires_image_then_saves(self):
        task = self._task()
        url = reverse('homework:step_create', args=[task.pk, 'mira'])
        self.client.post(url, {'question': '¿Qué ves?'})
        self.assertEqual(task.steps.count(), 0)
        media = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, media, True)
        with override_settings(MEDIA_ROOT=media):
            self.client.post(url, {'question': '¿Qué ves?', 'image': SimpleUploadedFile('a.gif', GIF, 'image/gif')})
        step = task.steps.get()
        self.assertEqual(step.payload, {'question': '¿Qué ves?'})
        self.assertTrue(step.image.name.startswith('tasks/'))

    def test_lectura_step_requires_reading_or_text(self):
        task = self._task()
        url = reverse('homework:step_create', args=[task.pk, 'lectura'])
        self.assertEqual(self.client.post(url, {}).status_code, 200)
        self.assertEqual(task.steps.count(), 0)
        self.client.post(url, {'text': 'El sol sale.'})
        self.assertEqual(task.steps.get().payload, {'text': 'El sol sale.'})

    def test_lectura_step_with_library_reading(self):
        task = self._task()
        reading = Reading.objects.create(title='R', content='Contenido', level=self.level, grade='1')
        self.client.post(reverse('homework:step_create', args=[task.pk, 'lectura']), {'reading': reading.pk})
        step = task.steps.get()
        self.assertEqual(step.reading, reading)
        self.assertEqual(step.text, 'Contenido')

    def test_lectura_reading_choices_match_task_grade(self):
        task = self._task(grade='1')
        mine = Reading.objects.create(title='Uno', content='c', level=self.level, grade='1')
        Reading.objects.create(title='Dos', content='c', level=self.level, grade='2')
        Reading.objects.create(title='Inactiva', content='c', level=self.level, grade='1', is_active=False)
        form = LecturaStepForm(task=task)
        self.assertEqual(list(form.fields['reading'].queryset), [mine])

    def test_unregistered_step_type_is_404(self):
        task = self._task()
        self.assertEqual(self.client.get(reverse('homework:step_create', args=[task.pk, 'desconocido'])).status_code, 404)
        self.assertEqual(self.client.post(reverse('homework:step_create', args=[task.pk, 'desconocido'])).status_code, 404)
        self.assertEqual(set(STEP_FORMS), {'mira', 'lectura', 'palabras', 'contesta', 'arma', 'ejemplo'})

    def test_update_step_changes_payload(self):
        task = self._task()
        step = append_step(task, 'lectura', {'text': 'Viejo'})
        self.client.post(reverse('homework:step_update', args=[task.pk, step.pk]), {'text': 'Nuevo'})
        step.refresh_from_db()
        self.assertEqual(step.payload, {'text': 'Nuevo'})

    def test_delete_and_move_views(self):
        task = self._task()
        first = append_step(task, 'lectura', {'text': 'Uno'})
        second = append_step(task, 'lectura', {'text': 'Dos'})
        self.client.post(reverse('homework:step_move', args=[task.pk, second.pk]), {'direction': 'up'})
        self.assertEqual([s.pk for s in task.steps.all()], [second.pk, first.pk])
        self.client.post(reverse('homework:step_delete', args=[task.pk, second.pk]))
        self.assertEqual(list(task.steps.values_list('pk', 'order')), [(first.pk, 1)])

    def test_step_of_another_task_is_404(self):
        task = self._task()
        other = self._task(title='Otra')
        step = append_step(other, 'lectura', {'text': 'x'})
        self.assertEqual(self.client.post(reverse('homework:step_delete', args=[task.pk, step.pk])).status_code, 404)

    def test_other_teacher_gets_404_on_step_changes(self):
        task = self._task(teacher=self.other_teacher)
        step = append_step(task, 'lectura', {'text': 'x'})
        self.assertEqual(self.client.post(reverse('homework:step_delete', args=[task.pk, step.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('homework:step_create', args=[task.pk, 'lectura'])).status_code, 404)

    def test_locked_task_refuses_step_changes_by_post(self):
        task = self._task()
        step = append_step(task, 'lectura', {'text': 'Uno'})
        append_step(task, 'lectura', {'text': 'Dos'})
        TaskAssignment.objects.create(task=task, student=self.ana, started_at=timezone.now())
        detail = reverse('homework:task_detail', args=[task.pk])
        responses = [
            self.client.post(reverse('homework:step_create', args=[task.pk, 'lectura']), {'text': 'Nuevo'}, follow=True),
            self.client.post(reverse('homework:step_update', args=[task.pk, step.pk]), {'text': 'Cambiado'}, follow=True),
            self.client.post(reverse('homework:step_delete', args=[task.pk, step.pk]), follow=True),
            self.client.post(reverse('homework:step_move', args=[task.pk, step.pk]), {'direction': 'down'}, follow=True),
        ]
        for response in responses:
            self.assertRedirects(response, detail)
            self.assertContains(response, LOCK_MESSAGE)
        self.assertEqual(list(task.steps.values_list('order', 'payload')), [(1, {'text': 'Uno'}), (2, {'text': 'Dos'})])

    def test_locked_detail_hides_edit_controls_and_shows_notice(self):
        task = self._task()
        append_step(task, 'lectura', {'text': 'Uno'})
        TaskAssignment.objects.create(task=task, student=self.ana, started_at=timezone.now())
        response = self.client.get(reverse('homework:task_detail', args=[task.pk]))
        self.assertContains(response, LOCK_MESSAGE)
        self.assertNotContains(response, 'Agregar paso')
        self.assertNotContains(response, 'Eliminar')

    def test_unlocked_detail_lists_steps_with_summary_and_add_dialog(self):
        task = self._task()
        append_step(task, 'contesta', {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': ['a', 'b'], 'answer': 'a'})
        response = self.client.get(reverse('homework:task_detail', args=[task.pk]))
        self.assertContains(response, '¿Qué come el conejo?')
        self.assertContains(response, 'Agregar paso')
        self.assertContains(response, reverse('homework:step_create', args=[task.pk, 'mira']))

    def test_duplicate_view_redirects_to_copy(self):
        task = self._task()
        append_step(task, 'lectura', {'text': 'Uno'})
        response = self.client.post(reverse('homework:task_duplicate', args=[task.pk]))
        copy = Task.objects.exclude(pk=task.pk).get()
        self.assertRedirects(response, reverse('homework:task_detail', args=[copy.pk]), fetch_redirect_response=False)
        self.assertEqual(copy.steps.count(), 1)

    def test_duplicate_requires_post_and_ownership(self):
        task = self._task(teacher=self.other_teacher)
        self.assertEqual(self.client.post(reverse('homework:task_duplicate', args=[task.pk])).status_code, 404)
        own = self._task()
        self.assertEqual(self.client.get(reverse('homework:task_duplicate', args=[own.pk])).status_code, 405)


class PalabrasFormTests(TeacherTaskTestCase):
    def _form(self, task, words):
        return PalabrasStepForm({'words': words}, task=task)

    def test_palabras_form_initial_proposes_words_from_lectura(self):
        task = self._task()
        append_step(task, 'lectura', {'text': 'El murciélago y la mariposa leyeron un libro'})
        value = PalabrasStepForm(task=task)['words'].value()
        self.assertEqual(value.splitlines()[:3], ['murciélago', 'mariposa', 'leyeron'])

    def test_palabras_form_initial_uses_library_reading(self):
        task = self._task()
        reading = Reading.objects.create(title='R', content='Mariposa de colores', level=self.level, grade='1')
        append_step(task, 'lectura', {'text': ''}, reading=reading)
        self.assertIn('mariposa', PalabrasStepForm(task=task)['words'].value().splitlines())

    def test_palabras_form_initial_empty_without_lectura(self):
        self.assertFalse(PalabrasStepForm(task=self._task())['words'].value())

    def test_palabras_form_saves_words_payload(self):
        task = self._task()
        form = self._form(task, 'sol\nluna\n  mar \n\n')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.to_payload(), {'words': ['sol', 'luna', 'mar']})

    def test_palabras_form_rejects_wrong_count_digits_and_long_words(self):
        task = self._task()
        for words in ('sol\nluna', 'a\nb\nc\nd\ne\nf\ng', 'sol\nluna\nmar2', 'sol\nluna\nel sol', 'sol\nluna\n' + 'a' * 31):
            self.assertFalse(self._form(task, words).is_valid(), words)

    def test_palabras_step_created_and_edited_through_views(self):
        task = self._task()
        self.client.post(reverse('homework:step_create', args=[task.pk, 'palabras']), {'words': 'sol\nluna\nmar'})
        step = task.steps.get()
        self.assertEqual(step.payload, {'words': ['sol', 'luna', 'mar']})
        response = self.client.get(reverse('homework:step_update', args=[task.pk, step.pk]))
        self.assertEqual(response.context['form']['words'].value(), 'sol\nluna\nmar')
