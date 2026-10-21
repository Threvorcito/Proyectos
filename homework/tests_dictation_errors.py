"""Dictation error types (MINED Tomo I, Educación Especial): classification, summary, report and instrument."""
from types import SimpleNamespace

from django.test import SimpleTestCase
from django.urls import reverse
from django.utils import timezone

from .dictation import DictationError, ErrorType, classify, error_summary
from .models import TaskAssignment
from .reports import task_rows
from .tests_dictation_report import SENTENCES, WORDS, DictationReportTestCase

# Carla confuses m with n in "mesa"; everything else right.
CONFUSES_M_N = ['nesa', *WORDS[1:], *SENTENCES]


class ClassifyTests(SimpleTestCase):
    def test_omissions(self):
        errors = classify('contento', 'conto', 'letter')
        self.assertEqual(len(errors), 3)
        self.assertTrue(all(error.kind == ErrorType.OMISSION for error in errors))

    def test_confusions(self):
        self.assertEqual(classify('mesa', 'nesa', 'letter'), [DictationError(ErrorType.CONFUSION, 'm–n')])
        self.assertEqual(classify('dedo', 'bedo', 'letter'), [DictationError(ErrorType.CONFUSION, 'b–d')])

    def test_inversion(self):
        self.assertEqual(classify('sol', 'slo', 'letter'), [DictationError(ErrorType.INVERSION, '')])

    def test_substitution(self):
        self.assertEqual(classify('mesa', 'mosa', 'letter'), [DictationError(ErrorType.SUBSTITUTION, '')])

    def test_accents_and_case_ignored(self):
        self.assertEqual(classify('Mamá', 'mama', 'letter'), [])

    def test_sentences(self):
        self.assertEqual(classify('Mi mamá me ama.', 'Mi me ama', 'word'), [DictationError(ErrorType.OMISSION, 'mamá')])
        self.assertEqual(classify('Amo a mi mamá.', 'a Amo mi mamá', 'word'), [DictationError(ErrorType.INVERSION, '')])

    def test_empty_answer(self):
        self.assertEqual(classify('mesa', '', 'letter'), [DictationError(ErrorType.OMISSION, '')])


class ErrorSummaryTests(SimpleTestCase):
    def test_summary_counts_completed_first_answers(self):
        payload = {'letter': 'r', 'words': ['rosa', 'mesa', 'arco', 'cama', 'lima'], 'sentences': SENTENCES}
        done = timezone.now()

        def result(answer, completed_at=done):
            return SimpleNamespace(first_answer=answer, completed_at=completed_at)

        results = {
            0: result('osa'),
            1: result('nesa'),
            2: result('aco'),
            3: result('cama'),
            4: result('xyz', completed_at=None),
        }
        self.assertEqual(error_summary(payload, results), [('Omisión «r»', 2), ('Confusión m–n', 1)])


class ErrorsInReportTests(DictationReportTestCase):
    def setUp(self):
        super().setUp()
        self.confused = TaskAssignment.objects.create(task=self.task, student=self.carla)
        self._answer(self.confused, CONFUSES_M_N)

    def test_task_rows_errors(self):
        rows = {row['student'].name: row for row in task_rows(self.task, self._assignments())}
        self.assertEqual(rows['Carla']['errors'], [('Confusión m–n', 1)])
        self.assertEqual(rows['Beto']['errors'], [])

    def test_report_shows_frequent_errors(self):
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertContains(response, 'Errores frecuentes')
        self.assertContains(response, 'Confusión m–n')
        self.assertNotContains(response, 'dislexia')

    def test_report_hides_errors_without_report_permission(self):
        self.teacher.can_view_student_reports = False
        self.teacher.save()
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        rows = {row['student'].name: row for row in response.context['rows']}
        self.assertEqual(rows['Carla']['errors'], [])
        self.assertNotContains(response, 'Errores frecuentes')
        self.assertNotContains(response, 'Confusión m–n')

    def instrument(self):
        return self.client.get(reverse('homework:dictation_instrument', args=[self.task.pk, self.step.pk]))

    def test_instrument_shows_errors(self):
        response = self.instrument()
        self.assertContains(response, 'Errores frecuentes')
        self.assertContains(response, 'Confusión m–n')
        self.assertNotContains(response, 'dislexia')
        sheet = {row['student'].name: row for row in response.context['sheet']}
        self.assertEqual(sheet['Carla']['errors'], [('Confusión m–n', 1)])

    def test_instrument_hides_errors_without_report_permission(self):
        self.teacher.can_view_student_reports = False
        self.teacher.save()
        response = self.instrument()
        sheet = {row['student'].name: row for row in response.context['sheet']}
        self.assertEqual(sheet['Carla']['errors'], [])
        self.assertNotContains(response, 'Confusión m–n')
