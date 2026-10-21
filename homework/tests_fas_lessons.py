"""Secuencia FAS page and the daily FAS class it builds."""
import re

from django.contrib.messages import get_messages
from django.urls import reverse

from accounts.models import CustomUser
from learning.models import ParentProfile, StudentProfile, Subject

from .fas_lessons import build_daily_class, letter_statuses
from .fas_sequence import CONSONANTS
from .models import Task
from .services import assign_students
from .tests_teacher import TeacherTaskTestCase

SEQUENCE_URL = reverse('homework:fas_sequence')


def create_url(letter):
    return reverse('homework:fas_class_create', args=[letter])


def tile_count(html, letter):
    return len(re.findall(rf'data-letter="{letter}"', html))


class BuildDailyClassTests(TeacherTaskTestCase):
    def test_build_daily_class_steps(self):
        task = build_daily_class(self.teacher, 'm', self.subject)
        steps = list(task.steps.all())
        self.assertEqual([step.step_type for step in steps], ['mira', 'palabras', 'arma', 'arma', 'lectura', 'dictado'])
        self.assertEqual(task.title, 'Clase FAS de la «m»')
        self.assertEqual(task.grade, StudentProfile.Grade.FIRST)
        self.assertEqual(steps[0].payload['question'], 'El sonido de hoy: mmm. ¿Qué palabras tienen este sonido?')
        self.assertEqual(steps[2].payload, {'text': 'mamá', 'unit': 'syllable'})
        self.assertEqual(steps[3].payload, {'text': 'Mamá me ama.', 'unit': 'word'})
        self.assertEqual(steps[5].payload['letter'], 'm')
        self.assertEqual(len(steps[5].payload['words']), 5)

    def test_stop_sound_is_letter_with_a(self):
        task = build_daily_class(self.teacher, 'p', self.subject)
        self.assertIn('El sonido de hoy: pa.', task.steps.first().payload['question'])

    def test_build_unknown_letter(self):
        with self.assertRaises(ValueError):
            build_daily_class(self.teacher, 'r', self.subject)
        self.assertFalse(Task.objects.exists())


class FasSequencePageTests(TeacherTaskTestCase):
    def test_sequence_page_lists_groups(self):
        response = self.client.get(SEQUENCE_URL)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('Aprestamiento', html)
        for letter in CONSONANTS:
            self.assertEqual(tile_count(html, letter), 1, letter)
        self.assertIn(f'action="{create_url("m")}"', html)
        self.assertNotIn(f'action="{create_url("r")}"', html)

    def test_task_list_links_sequence(self):
        self.assertContains(self.client.get(reverse('homework:task_list')), f'href="{SEQUENCE_URL}"')

    def test_create_posts_and_redirects(self):
        response = self.client.post(create_url('m'))
        task = Task.objects.get()
        self.assertRedirects(response, reverse('homework:task_detail', args=[task.pk]))
        self.assertEqual(task.teacher, self.teacher)
        self.assertEqual(task.subject, self.subject)
        self.assertEqual(task.steps.count(), 6)
        self.assertIn('Clase de la «m» creada', [str(m) for m in get_messages(response.wsgi_request)][0])

    def test_status_after_create_and_assign(self):
        self.assertContains(self.client.get(SEQUENCE_URL), 'Sin clase')
        self.client.post(create_url('m'))
        self.assertEqual(letter_statuses(self.teacher), {'m': 'created'})
        self.assertContains(self.client.get(SEQUENCE_URL), 'Clase creada')
        assign_students(Task.objects.get(), [self.ana])
        self.assertEqual(letter_statuses(self.teacher), {'m': 'assigned'})
        self.assertContains(self.client.get(SEQUENCE_URL), 'Asignada')

    def test_assigned_wins_over_created(self):
        assign_students(build_daily_class(self.teacher, 'm', self.subject), [self.ana])
        build_daily_class(self.teacher, 'm', self.subject)
        self.assertEqual(letter_statuses(self.teacher), {'m': 'assigned'})

    def test_statuses_ignore_archived_and_other_teachers(self):
        build_daily_class(self.other_teacher, 'm', self.subject)
        archived = build_daily_class(self.teacher, 'p', self.subject)
        archived.is_active = False
        archived.save()
        self.assertEqual(letter_statuses(self.teacher), {})

    def test_statuses_use_fixed_queries(self):
        for letter in ('m', 'p', 'b'):
            assign_students(build_daily_class(self.teacher, letter, self.subject), [self.ana])
        with self.assertNumQueries(1):
            letter_statuses(self.teacher)

    def test_double_create(self):
        self.client.post(create_url('m'))
        self.client.post(create_url('m'))
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual(tile_count(self.client.get(SEQUENCE_URL).content.decode(), 'm'), 1)

    def test_permissions(self):
        denied = reverse('dashboard:teacher')
        CustomUser.objects.create_user(username='papa', password='x', role='PARENT', email='papa@example.com')
        ParentProfile.objects.create(user=CustomUser.objects.get(username='papa'), name='Papá').students.add(self.ana)
        self._teacher('sinpermiso', 'Maestra Sin Permiso')
        for username in ('ana', 'papa', 'sinpermiso'):
            self.client.login(username=username, password='x')
            self.assertRedirects(self.client.get(SEQUENCE_URL), denied, fetch_redirect_response=False)
            self.assertRedirects(self.client.post(create_url('m')), denied, fetch_redirect_response=False)
        self.assertFalse(Task.objects.exists())
        self.client.login(username='maestra', password='x')
        self.assertEqual(self.client.get(create_url('m')).status_code, 405)

    def test_create_requires_csrf(self):
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.login(username='maestra', password='x')
        self.assertEqual(client.post(create_url('m')).status_code, 403)
        self.assertFalse(Task.objects.exists())

    def test_unknown_letter_404(self):
        for letter in ('r', 'qq'):
            self.assertEqual(self.client.post(create_url(letter)).status_code, 404)
        self.assertFalse(Task.objects.exists())

    def test_missing_subject(self):
        Subject.objects.filter(name='Lengua y Literatura').delete()
        response = self.client.post(create_url('m'))
        self.assertRedirects(response, SEQUENCE_URL)
        self.assertFalse(Task.objects.exists())
        [message] = get_messages(response.wsgi_request)
        self.assertEqual(message.level_tag, 'error')
