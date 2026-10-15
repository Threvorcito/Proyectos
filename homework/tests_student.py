import json

from django.urls import reverse

from learning.models import LessonPlan, LessonPlanAssignment

from .models import StepResult, TaskAssignment
from .services import append_step
from .tests_teacher import TeacherTaskTestCase

CHOICE = {'question': '¿Qué come el conejo?', 'kind': 'choice', 'options': ['piedra', 'zanahoria'], 'answer': 'zanahoria'}
CARD = 'student-choice-card--task'


class StudentTaskTestCase(TeacherTaskTestCase):
    def setUp(self):
        super().setUp()
        self.task = self._task()
        self.mira = append_step(self.task, 'mira', {'question': 'Mira el conejo'}, image='tasks/x.gif')
        self.contesta = append_step(self.task, 'contesta', dict(CHOICE))
        self.assignment = TaskAssignment.objects.create(task=self.task, student=self.ana)
        self.client.login(username='ana', password='x')

    def path_url(self, assignment=None):
        return reverse('homework:student_task', args=[(assignment or self.assignment).pk])

    def step_url(self, order, name='student_step', assignment=None):
        return reverse(f'homework:{name}', args=[(assignment or self.assignment).pk, order])

    def post(self, order, name, body):
        return self.client.post(self.step_url(order, name), data=json.dumps(body), content_type='application/json')


class DashboardCardTests(StudentTaskTestCase):
    def test_dashboard_shows_task_card_above_choices(self):
        html = self.client.get(reverse('dashboard:student')).content.decode()
        self.assertIn('Mi tarea de hoy', html)
        self.assertIn(self.path_url(), html)
        self.assertLess(html.index(CARD), html.index('student-choice-card--practice'))

    def test_dashboard_hides_archived_and_empty_tasks(self):
        self.assignment.delete()
        archived = self._task(title='Archivada', is_active=False)
        append_step(archived, 'mira', {'question': 'Q'}, image='tasks/x.gif')
        empty = self._task(title='Vacía')
        for task in (archived, empty):
            TaskAssignment.objects.create(task=task, student=self.ana)
        self.assertNotContains(self.client.get(reverse('dashboard:student')), CARD)

    def test_existing_lesson_plan_block_still_rendered(self):
        plan = self._plan(self.teacher, status=LessonPlan.Status.ACTIVE)
        LessonPlanAssignment.objects.create(plan=plan, student=self.ana, is_active=True)
        response = self.client.get(reverse('dashboard:student'))
        self.assertContains(response, 'Mi clase de hoy')
        self.assertContains(response, CARD)


class PathAndStepPageTests(StudentTaskTestCase):
    def test_path_marks_current_step_and_never_shows_levels(self):
        response = self.client.get(self.path_url())
        self.assertContains(response, 'aria-current="step"', count=1)
        self.assertContains(response, '¡Vamos!')
        self.assertContains(response, self.step_url(1))
        self.assertNotContains(response, 'Aprendizaje')

    def test_student_cannot_open_other_students_assignment(self):
        other = TaskAssignment.objects.create(task=self.task, student=self.beto)
        self.assertEqual(self.client.get(self.path_url(other)).status_code, 404)
        self.assertEqual(self.client.get(self.step_url(1, assignment=other)).status_code, 404)
        response = self.client.post(self.step_url(1, 'step_done', other), data='{"item_index": 0}', content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(StepResult.objects.filter(assignment=other).exists())

    def test_archived_and_empty_tasks_are_404(self):
        self.task.is_active = False
        self.task.save()
        self.assertEqual(self.client.get(self.path_url()).status_code, 404)
        empty = TaskAssignment.objects.create(task=self._task(title='Vacía'), student=self.ana)
        self.assertEqual(self.client.get(self.path_url(empty)).status_code, 404)
        self.assertEqual(self.client.get(self.step_url(1, assignment=empty)).status_code, 404)

    def test_opening_first_step_starts_assignment(self):
        response = self.client.get(self.step_url(1))
        self.assertContains(response, 'Mira el conejo')
        self.assertContains(response, 'data-task-done="0"')
        self.assertContains(response, 'kid-listen')
        self.assignment.refresh_from_db()
        self.assertIsNotNone(self.assignment.started_at)

    def test_future_step_redirects_to_path(self):
        response = self.client.get(self.step_url(2))
        self.assertRedirects(response, self.path_url(), fetch_redirect_response=False)

    def test_contesta_step_renders_one_button_per_option(self):
        self.post(1, 'step_done', {'item_index': 0})
        response = self.client.get(self.step_url(2))
        self.assertContains(response, 'data-task-choice=', count=2)
        self.assertContains(response, 'piedra')
        self.assertNotContains(response, 'incorrecto')

    def test_hecho_flag_makes_lumi_cheer(self):
        self.assertContains(self.client.get(self.path_url() + '?hecho=1'), 'data-mascot-on-load="cheer"')


class StepJsonTests(StudentTaskTestCase):
    def test_step_done_json_flow_completes_task(self):
        first = self.post(1, 'step_done', {'item_index': 0})
        self.assertEqual(first.json()['step_done'], True)
        self.assertEqual(first.json()['task_done'], False)
        self.assertEqual(first.json()['next_url'], self.path_url() + '?hecho=1')
        last = self.post(2, 'step_answer', {'item_index': 0, 'choice': 1}).json()
        self.assertEqual((last['status'], last['task_done']), ('correct', True))
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.status, TaskAssignment.Status.COMPLETED)
        self.assertContains(self.client.get(self.path_url()), '¡Terminaste tu tarea!')

    def test_step_answer_try_again_then_modeled(self):
        self.post(1, 'step_done', {'item_index': 0})
        first = self.post(2, 'step_answer', {'item_index': 0, 'choice': 0}).json()
        self.assertEqual(first['status'], 'try_again')
        self.assertEqual(first['step_done'], False)
        self.assertIsNone(first['next_url'])
        body = self.post(2, 'step_answer', {'item_index': 0, 'choice': 0}).json()
        self.assertEqual((body['status'], body['model_answer']), ('modeled', 'zanahoria'))
        self.assertEqual(body['step_done'], True)

    def test_step_answer_bad_payload_400_and_closed_409(self):
        self.post(1, 'step_done', {'item_index': 0})
        for body in ({'item_index': 0}, {'item_index': 0, 'choice': 9}, {'item_index': True, 'choice': 0}, {'choice': 0}, {'item_index': -1, 'choice': 0}):
            response = self.post(2, 'step_answer', body)
            self.assertEqual(response.status_code, 400, body)
            self.assertEqual(response.json(), {'saved': False, 'reason': 'payload'})
        self.assertEqual(self.client.post(self.step_url(2, 'step_answer'), data='nope', content_type='application/json').status_code, 400)
        self.post(2, 'step_answer', {'item_index': 0, 'choice': 1})
        closed = self.post(2, 'step_answer', {'item_index': 0, 'choice': 1})
        self.assertEqual(closed.status_code, 409)
        self.assertEqual(closed.json()['reason'], 'closed')
        self.assertEqual(StepResult.objects.get(step=self.contesta).attempts, 1)

    def test_item_index_zero_is_accepted_and_evaluated_steps_refuse_done(self):
        self.assertEqual(self.post(1, 'step_done', {'item_index': 0}).status_code, 200)
        self.assertEqual(self.post(2, 'step_done', {'item_index': 0}).status_code, 400)

    def test_missing_step_is_404_json(self):
        response = self.post(9, 'step_done', {'item_index': 0})
        self.assertEqual((response.status_code, response.json()['reason']), (404, 'step'))

    def test_get_is_not_allowed_on_json_endpoints(self):
        self.assertEqual(self.client.get(self.step_url(1, 'step_done')).status_code, 405)

    def test_teacher_cannot_post_child_answers(self):
        self.client.login(username='maestra', password='x')
        response = self.post(1, 'step_done', {'item_index': 0})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(StepResult.objects.exists())

    def test_cannot_skip_ahead_on_done_or_answer(self):
        done = self.post(2, 'step_done', {'item_index': 0})
        answer = self.post(2, 'step_answer', {'item_index': 0, 'choice': 1})
        for response in (done, answer):
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['reason'], 'step')
        self.assertFalse(StepResult.objects.exists())

    def test_closed_earlier_step_keeps_friendly_409(self):
        self.post(1, 'step_done', {'item_index': 0})
        self.post(2, 'step_answer', {'item_index': 0, 'choice': 1})
        again = self.post(2, 'step_answer', {'item_index': 0, 'choice': 1})
        self.assertEqual((again.status_code, again.json()['reason']), (409, 'closed'))

    def test_dashboard_card_subtitle(self):
        self.assertContains(self.client.get(reverse('dashboard:student')), 'Tu profe preparó pasos para ti')
