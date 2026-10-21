"""Dictado break point in the teacher report, the printable instrument, and the family never seeing it (Ley 787)."""
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from learning.models import ParentProfile

from .dictation import BreakPoint
from .models import StepResult, TaskAssignment
from .reports import break_point_groups, task_rows
from .services import append_step
from .tests_teacher import TeacherTaskTestCase

WORDS = ['mesa', 'mamá', 'cama', 'lima', 'humo']
SENTENCES = ['Mi mamá me ama.', 'Amo a mi mamá.']
PAYLOAD = {'letter': 'm', 'words': WORDS, 'sentences': SENTENCES}
# Only "humo" keeps its m: the sound-letter criterion fails (1 of 5).
SOUND_LETTER_FAILS = ['esa', 'amá', 'caa', 'lia', 'humo', *SENTENCES]
CRITERION_HEADERS = ('Sonido-letra', 'Palabras', 'Oraciones')


class DictationReportTestCase(TeacherTaskTestCase):
    def setUp(self):
        super().setUp()
        self.teacher.can_view_student_reports = True
        self.teacher.save()
        self.task = self._task(title='Dictado de la m')
        self.step = append_step(self.task, 'dictado', dict(PAYLOAD))
        self.done = TaskAssignment.objects.create(
            task=self.task, student=self.ana, status='completed', started_at=timezone.now(), completed_at=timezone.now(),
        )
        self.pending = TaskAssignment.objects.create(task=self.task, student=self.beto)
        self._answer(self.done, SOUND_LETTER_FAILS)

    def _answer(self, assignment, answers):
        targets = [*WORDS, *SENTENCES]
        for index, answer in enumerate(answers):
            StepResult.objects.create(
                assignment=assignment, step=self.step, item_index=index, attempts=1, first_answer=answer,
                answer=targets[index], first_try_correct=answer == targets[index], completed_at=timezone.now(),
            )

    def _assignments(self):
        return self.task.assignments.select_related('student').order_by('student__name', 'pk')


class TaskRowsTests(DictationReportTestCase):
    def test_task_rows_break_point(self):
        rows = {row['student'].name: row for row in task_rows(self.task, self._assignments())}
        self.assertEqual(rows['Ana']['break_point'], BreakPoint.SOUND_LETTER)
        self.assertFalse(rows['Ana']['criteria'].sound_letter)
        self.assertTrue(rows['Ana']['criteria'].sentences)
        self.assertEqual(rows['Beto']['break_point'], BreakPoint.INCOMPLETE)
        self.assertIsNone(rows['Beto']['criteria'])

    def test_task_without_dictado_has_no_break_point(self):
        task = self._task(title='Sin dictado')
        append_step(task, 'palabras', {'words': ['mesa', 'cama', 'lima']})
        TaskAssignment.objects.create(task=task, student=self.ana)
        [row] = task_rows(task, task.assignments.select_related('student'))
        self.assertIsNone(row['break_point'])
        self.assertIsNone(row['criteria'])

    def test_task_rows_query_count(self):
        def count_queries(assignments):
            assignments = list(assignments)
            with CaptureQueriesContext(connection) as queries:
                rows = task_rows(self.task, assignments)
                [row['break_point'] for row in rows]
            return len(rows), len(queries)

        one = count_queries(self._assignments().filter(student=self.ana))
        self._answer(TaskAssignment.objects.create(task=self.task, student=self.carla), [*WORDS, *SENTENCES])
        three = count_queries(self._assignments())
        self.assertEqual((one[0], three[0]), (1, 3))
        self.assertEqual(one[1], three[1])

    def test_break_point_groups_order_and_omit_empty(self):
        rows = [
            {'student': 'Ana', 'break_point': BreakPoint.NONE},
            {'student': 'Beto', 'break_point': BreakPoint.INCOMPLETE},
            {'student': 'Carla', 'break_point': BreakPoint.SOUND_LETTER},
            {'student': 'Dani', 'break_point': None},
            {'student': 'Eva', 'break_point': BreakPoint.SOUND_LETTER},
        ]
        self.assertEqual(break_point_groups(rows), [
            ('Sonido-letra', ['Carla', 'Eva']),
            ('Incompleto', ['Beto']),
            ('Sin quiebre', ['Ana']),
        ])


class TaskReportTests(DictationReportTestCase):
    def test_report_groups_by_break_point(self):
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertContains(response, 'Agrupar para reforzar')
        self.assertContains(response, 'Punto de quiebre')
        self.assertEqual(response.context['groups'], [('Sonido-letra', [self.ana]), ('Incompleto', [self.beto])])
        self.assertContains(response, 'Sonido-letra')
        self.assertContains(response, 'Incompleto')

    def test_report_hides_break_point_without_report_permission(self):
        self.teacher.can_view_student_reports = False
        self.teacher.save()
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertEqual(response.context['groups'], [])
        self.assertNotContains(response, 'Punto de quiebre')
        self.assertNotContains(response, 'Sonido-letra')

    def test_task_detail_links_instrument(self):
        response = self.client.get(reverse('homework:task_detail', args=[self.task.pk]))
        self.assertContains(response, reverse('homework:dictation_instrument', args=[self.task.pk, self.step.pk]))


class InstrumentTests(DictationReportTestCase):
    def url(self, step=None):
        return reverse('homework:dictation_instrument', args=[self.task.pk, (step or self.step).pk])

    def test_instrument_lists_items_and_students(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        for text in ['«m»', *WORDS, *SENTENCES, 'Ana', 'Beto', *CRITERION_HEADERS, 'Punto de quiebre', 'data-dictation-print', 'css/homework.css']:
            self.assertContains(response, text)
        [ana, beto] = response.context['sheet']
        # Pre-marked from the app: only the last word and both sentences right on the first try.
        self.assertEqual(ana['marks'], [False, False, False, False, True, True, True])
        self.assertEqual(ana['break_point'], BreakPoint.SOUND_LETTER)
        self.assertEqual(beto['marks'], [None] * 7)

    def test_instrument_hides_marks_without_report_permission(self):
        self.teacher.can_view_student_reports = False
        self.teacher.save()
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        [ana, _beto] = response.context['sheet']
        self.assertEqual(ana['marks'], [None] * 7)
        self.assertIsNone(ana['break_point'])
        self.assertNotContains(response, 'Sonido-letra</td>')

    def test_instrument_rejects_non_dictado_step(self):
        other = append_step(self.task, 'palabras', {'words': ['mesa', 'cama', 'lima']})
        self.assertEqual(self.client.get(self.url(other)).status_code, 404)
        foreign = self._task(title='Otra')
        foreign_step = append_step(foreign, 'dictado', dict(PAYLOAD))
        self.assertEqual(self.client.get(self.url(foreign_step)).status_code, 404)

    def test_instrument_permissions(self):
        report = reverse('homework:task_report', args=[self.task.pk])
        self.client.login(username='maestro2', password='x')
        self.assertEqual(self.client.get(report).status_code, 404)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        parent_user = CustomUser.objects.create_user(username='papa', password='x', role='PARENT', email='papa@example.com')
        ParentProfile.objects.create(user=parent_user, name='Papá').students.add(self.ana)
        for username in ('papa', 'ana'):
            self.client.login(username=username, password='x')
            self.assertRedirects(self.client.get(self.url()), reverse('dashboard:teacher'), fetch_redirect_response=False)


class FamilyTests(DictationReportTestCase):
    def test_parent_dashboard_hides_break_point(self):
        parent_user = CustomUser.objects.create_user(username='papa', password='x', role='PARENT', email='papa@example.com')
        ParentProfile.objects.create(user=parent_user, name='Papá').students.add(self.ana, self.beto)
        self.client.login(username='papa', password='x')
        response = self.client.get(reverse('dashboard:parents'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dictado de la m')
        for label in BreakPoint.labels:
            self.assertNotContains(response, label)
        self.assertNotContains(response, 'quiebre')
