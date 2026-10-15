from .levels import suggest_for_assignment, suggest_snepa
from .models import StepResult, TaskAssignment
from .services import append_step, mark_item_done, record_decode_help, submit_answer
from .tests_progress import CHOICE, ProgressTestCase


class ThresholdTests(ProgressTestCase):
    def test_thresholds(self):
        self.assertEqual(suggest_snepa(10, 9, 2), 'AA')
        self.assertEqual(suggest_snepa(10, 9, 3), 'AS')  # help_rate 0.3
        self.assertEqual(suggest_snepa(10, 7, 7), 'AS')
        self.assertEqual(suggest_snepa(10, 7, 8), 'AF')
        self.assertEqual(suggest_snepa(10, 4, 20), 'AF')
        self.assertEqual(suggest_snepa(10, 3, 0), 'AI')
        self.assertEqual(suggest_snepa(0, 0, 5), '')


class AssignmentSuggestionTests(ProgressTestCase):
    def test_palabras_decode_help_not_counted(self):
        palabras = append_step(self.task, 'palabras', {'words': ['sol', 'luna', 'mesa']})
        mark_item_done(self.a, self.mira, 0)
        record_decode_help(self.a, palabras, 'sol')
        record_decode_help(self.a, palabras, 'sol')
        StepResult.objects.filter(step=self.contesta).delete()
        StepResult.objects.create(assignment=self.a, step=self.contesta, attempts=1, first_try_correct=True)
        self.assertEqual(suggest_for_assignment(self.a), 'AA')
        record_decode_help(self.a, self.contesta, 'sol')
        record_decode_help(self.a, self.contesta, 'sol')
        self.assertEqual(suggest_for_assignment(self.a), 'AF')

    def test_hints_and_modeled_count_as_helps(self):
        StepResult.objects.create(
            assignment=self.a, step=self.contesta, attempts=2, first_try_correct=False, hints_used=1, modeled=True
        )
        # evaluated 1, correct 0 -> accuracy 0
        self.assertEqual(suggest_for_assignment(self.a), 'AI')

    def test_completion_stores_suggestion(self):
        mark_item_done(self.a, self.mira, 0)
        out = submit_answer(self.a, self.contesta, 0, {'choice': 0})
        self.assertTrue(out.task_done)
        self.assertEqual(TaskAssignment.objects.get().snepa_suggested, 'AA')
