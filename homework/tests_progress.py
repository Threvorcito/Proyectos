import datetime

from django.utils import timezone

from .evaluation import InvalidAnswer
from .models import StepResult, Task, TaskAssignment
from .services import (
    TASK_POINTS,
    ItemClosed,
    append_step,
    complete_assignment,
    current_step,
    ensure_editable,
    mark_item_done,
    next_assignment_for,
    start_assignment,
    step_states,
    submit_answer,
)
from .tests_teacher import TeacherTaskTestCase

CHOICE = {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': ['zanahoria', 'piedra'], 'answer': 'zanahoria'}


class ProgressTestCase(TeacherTaskTestCase):
    def setUp(self):
        super().setUp()
        self.task = self._task()
        self.mira = append_step(self.task, 'mira', {'question': 'Mira'}, image='tasks/x.gif')
        self.contesta = append_step(self.task, 'contesta', dict(CHOICE))
        self.a = TaskAssignment.objects.create(task=self.task, student=self.ana)


class NextAssignmentTests(ProgressTestCase):
    def test_next_assignment_prefers_nearest_due_date_then_undated(self):
        today = timezone.localdate()
        later = self._task(title='Tarde', due_date=today + datetime.timedelta(days=5))
        sooner = self._task(title='Pronto', due_date=today + datetime.timedelta(days=1))
        for t in (later, sooner):
            append_step(t, 'mira', {'question': 'Q'}, image='tasks/x.gif')
            TaskAssignment.objects.create(task=t, student=self.ana)
        self.assertEqual(next_assignment_for(self.ana).task, sooner)
        TaskAssignment.objects.filter(task__in=(later, sooner)).delete()
        self.assertEqual(next_assignment_for(self.ana).task, self.task)

    def test_dashboard_candidate_skips_completed_archived_and_empty(self):
        done = self._task(title='Hecha')
        archived = self._task(title='Archivada', is_active=False)
        empty = self._task(title='Vacía')
        for t in (done, archived):
            append_step(t, 'mira', {'question': 'Q'}, image='tasks/x.gif')
        TaskAssignment.objects.create(task=done, student=self.ana, status='completed')
        TaskAssignment.objects.create(task=archived, student=self.ana)
        TaskAssignment.objects.create(task=empty, student=self.ana)
        self.a.delete()
        self.assertIsNone(next_assignment_for(self.ana))


class StartAndStepTests(ProgressTestCase):
    def test_start_sets_started_once(self):
        start_assignment(self.a)
        first = TaskAssignment.objects.get().started_at
        self.assertIsNotNone(first)
        self.assertEqual(TaskAssignment.objects.get().status, 'in_progress')
        start_assignment(self.a)
        self.assertEqual(TaskAssignment.objects.get().started_at, first)

    def test_start_locks_task_for_editing(self):
        from .services import TaskLocked

        start_assignment(self.a)
        with self.assertRaises(TaskLocked):
            ensure_editable(self.task)

    def test_current_step_advances_after_mark_done(self):
        self.assertEqual(current_step(self.a), self.mira)
        mark_item_done(self.a, self.mira, 0)
        self.assertEqual(current_step(self.a), self.contesta)
        states = step_states(self.a)
        self.assertEqual([(s.done, s.current) for s in states], [(True, False), (False, True)])

    def test_mark_item_done_is_idempotent(self):
        first = mark_item_done(self.a, self.mira, 0)
        second = mark_item_done(self.a, self.mira, 0)
        self.assertEqual((first.status, second.status), ('done', 'done'))
        self.assertEqual(StepResult.objects.count(), 1)
        self.assertEqual((first.step_done, first.task_done), (True, False))

    def test_mark_item_done_rejects_evaluated_steps(self):
        with self.assertRaises(InvalidAnswer):
            mark_item_done(self.a, self.contesta, 0)
        self.assertFalse(StepResult.objects.exists())

    def test_item_index_out_of_range_rejected(self):
        with self.assertRaises(InvalidAnswer):
            mark_item_done(self.a, self.mira, 1)


class AnswerTests(ProgressTestCase):
    def test_correct_first_try(self):
        mark_item_done(self.a, self.mira, 0)
        out = submit_answer(self.a, self.contesta, 0, {'choice': 0})
        self.assertEqual((out.status, out.step_done, out.task_done), ('correct', True, True))
        r = StepResult.objects.get(step=self.contesta)
        self.assertTrue(r.first_try_correct)
        self.assertEqual(r.attempts, 1)
        self.assertEqual(r.answer, 'zanahoria')

    def test_wrong_then_wrong_models_answer(self):
        first = submit_answer(self.a, self.contesta, 0, {'choice': 1})
        self.assertEqual(first.status, 'try_again')
        self.assertEqual(first.hint['kind'], 'try_again')
        out = submit_answer(self.a, self.contesta, 0, {'choice': 1})
        self.assertEqual((out.status, out.model_answer), ('modeled', 'zanahoria'))
        r = StepResult.objects.get()
        self.assertEqual((r.first_try_correct, r.hints_used, r.modeled, r.first_answer), (False, 1, True, 'piedra'))

    def test_wrong_then_right_keeps_first_try_false(self):
        submit_answer(self.a, self.contesta, 0, {'choice': 1})
        out = submit_answer(self.a, self.contesta, 0, {'choice': 0})
        self.assertEqual(out.status, 'correct')
        r = StepResult.objects.get()
        self.assertEqual((r.first_try_correct, r.attempts, r.modeled, r.answer), (False, 2, False, 'zanahoria'))

    def test_answer_on_closed_item_raises(self):
        submit_answer(self.a, self.contesta, 0, {'choice': 0})
        with self.assertRaises(ItemClosed):
            submit_answer(self.a, self.contesta, 0, {'choice': 1})
        self.assertEqual(StepResult.objects.get().attempts, 1)

    def test_invalid_choice_raises_invalid_answer(self):
        for payload in ({'choice': 9}, {'choice': 'a'}, {}, {'choice': True}, {'choice': -1}):
            with self.assertRaises(InvalidAnswer):
                submit_answer(self.a, self.contesta, 0, payload)
        self.assertEqual(StepResult.objects.filter(attempts__gt=0).count(), 0)


class CompletionTests(ProgressTestCase):
    def test_complete_assignment_awards_once(self):
        mark_item_done(self.a, self.mira, 0)
        out = submit_answer(self.a, self.contesta, 0, {'choice': 0})
        self.assertTrue(out.task_done)
        self.ana.refresh_from_db()
        self.assertEqual((self.ana.points, self.ana.stars), (TASK_POINTS, 1))
        self.assertEqual(complete_assignment(self.a), 0)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.points, TASK_POINTS)
        a = TaskAssignment.objects.get()
        self.assertEqual((a.status, a.points_awarded), ('completed', TASK_POINTS))
        self.assertIsNotNone(a.completed_at)

    def test_complete_assignment_before_all_steps_done_awards_nothing(self):
        self.assertEqual(complete_assignment(self.a), 0)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.points, 0)
        self.assertEqual(TaskAssignment.objects.get().status, 'assigned')
