from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from core.models import AuditLog
from learning.models import Level, ParentProfile, StudentProfile, Subject, TeacherProfile

from .models import DecodeHelpEvent, OmissionEvent, StepResult, Task, TaskAssignment, TaskStep
from .permissions import can_view_difficulty_data

LEVEL_HEADER = '<th>Nivel</th>'


class ReportTestCase(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.owner = self._teacher('duena', can_assign_lesson_plans=True, can_view_student_reports=True)
        self.ana = self._student('ana', 'Ana')
        self.beto = self._student('beto', 'Beto')
        self.owner.students.add(self.ana, self.beto)
        self.task = Task.objects.create(teacher=self.owner, subject=self.subject, grade='1', title='Los animales')
        self.contesta = TaskStep.objects.create(
            task=self.task, order=1, step_type='contesta',
            payload={'question': '¿Quién lee?', 'kind': 'choice', 'options': ['Ana', 'Beto'], 'answer': 'Ana'},
        )
        self.palabras = TaskStep.objects.create(task=self.task, order=2, step_type='palabras', payload={'words': ['leyeron']})
        self.arma = TaskStep.objects.create(task=self.task, order=3, step_type='arma', payload={'text': 'ratón', 'unit': 'syllable'})
        self.assignment = TaskAssignment.objects.create(
            task=self.task, student=self.ana, status='completed', started_at=timezone.now(),
            completed_at=timezone.now(), snepa_suggested='AS',
        )
        TaskAssignment.objects.create(task=self.task, student=self.beto)
        StepResult.objects.create(
            assignment=self.assignment, step=self.contesta, attempts=2, first_answer='Beto', answer='Ana',
            first_try_correct=False, hints_used=1, modeled=False, completed_at=timezone.now(),
        )
        DecodeHelpEvent.objects.create(assignment=self.assignment, step=self.palabras, word='leyeron')
        OmissionEvent.objects.create(assignment=self.assignment, step=self.arma, target='ratón', missing_unit='ri', position=1)
        self.url = reverse('homework:assignment_report', args=[self.assignment.pk])

    def _user(self, username, role):
        return CustomUser.objects.create_user(username=username, password='x', role=role, email=f'{username}@example.com')

    def _teacher(self, username, **flags):
        return TeacherProfile.objects.create(user=self._user(username, 'TEACHER'), name=username, is_active=True, **flags)

    def _student(self, username, name):
        return StudentProfile.objects.create(
            user=self._user(username, 'STUDENT'), name=name, grade='1', reading_level=self.level, current_level=self.level,
        )


class AssignmentReportTests(ReportTestCase):
    def test_owner_with_report_permission_sees_detail(self):
        self.client.login(username='duena', password='x')
        response = self.client.get(self.url)
        self.assertContains(response, 'leyeron')
        self.assertContains(response, 'ri')
        self.assertContains(response, '¿Quién lee?')
        self.assertContains(response, 'Aprendizaje Satisfactorio')

    def test_detail_report_denied_without_report_permission_or_link(self):
        no_permission = self._teacher('sinpermiso', can_assign_lesson_plans=True)
        no_permission.students.add(self.ana)
        self._teacher('sinvinculo', can_view_student_reports=True)
        parent_user = self._user('papa', 'PARENT')
        ParentProfile.objects.create(user=parent_user, name='Papá').students.add(self.ana)
        self.owner.can_view_student_reports = False
        self.owner.save()
        for username in ('duena', 'sinpermiso', 'sinvinculo', 'papa', 'ana'):
            self.client.login(username=username, password='x')
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, 404, username)
            self.assertNotContains(response, 'leyeron', status_code=404)

    def test_linked_teacher_with_permission_who_is_not_owner_sees_detail(self):
        other = self._teacher('otra', can_view_student_reports=True)
        other.students.add(self.ana)
        self.client.login(username='otra', password='x')
        self.assertContains(self.client.get(self.url), 'leyeron')

    def test_admin_sees_detail(self):
        self._user('admin1', 'ADMIN')
        self.client.login(username='admin1', password='x')
        self.assertContains(self.client.get(self.url), 'leyeron')

    def test_override_level(self):
        self.client.login(username='duena', password='x')
        url = reverse('homework:assignment_level_update', args=[self.assignment.pk])
        self.client.post(url, {'level': 'AF'})
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.snepa_level, 'AF')
        self.assertEqual(self.assignment.snepa_override_by, self.owner)
        self.assertIsNotNone(self.assignment.snepa_override_at)
        self.assertTrue(AuditLog.objects.filter(action='override_task_level').exists())
        self.client.post(url, {'level': ''})
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.snepa_level, 'AS')
        self.assertIsNone(self.assignment.snepa_override_by)

    def test_override_denied_without_permission(self):
        self.owner.can_view_student_reports = False
        self.owner.save()
        self.client.login(username='duena', password='x')
        response = self.client.post(reverse('homework:assignment_level_update', args=[self.assignment.pk]), {'level': 'AA'})
        self.assertEqual(response.status_code, 404)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.snepa_override, '')

    def test_invalid_level_is_rejected(self):
        self.client.login(username='duena', password='x')
        self.client.post(reverse('homework:assignment_level_update', args=[self.assignment.pk]), {'level': 'ZZ'})
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.snepa_override, '')

    def test_no_data_label_when_nothing_suggested(self):
        self.assignment.snepa_suggested = ''
        self.assignment.save()
        self.client.login(username='duena', password='x')
        self.assertContains(self.client.get(self.url), 'Sin datos suficientes')


class TaskReportTests(ReportTestCase):
    def test_task_report_lists_rows_with_steps(self):
        self.client.login(username='duena', password='x')
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertContains(response, 'Ana')
        self.assertContains(response, 'Terminada')
        self.assertContains(response, 'Sin empezar')
        self.assertContains(response, '1/3')
        self.assertContains(response, LEVEL_HEADER)
        self.assertContains(response, self.url)

    def test_task_report_hides_level_column_without_permission(self):
        self.owner.can_view_student_reports = False
        self.owner.save()
        self.client.login(username='duena', password='x')
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertContains(response, 'Ana')
        self.assertNotContains(response, LEVEL_HEADER)
        self.assertNotContains(response, self.url)
        self.assertNotContains(response, 'Aprendizaje')

    def test_task_report_hides_unlinked_student_detail(self):
        self.owner.students.remove(self.ana)
        self.client.login(username='duena', password='x')
        response = self.client.get(reverse('homework:task_report', args=[self.task.pk]))
        self.assertNotContains(response, self.url)
        self.assertNotContains(response, 'Aprendizaje')

    def test_other_teacher_gets_404(self):
        self._teacher('otra', can_assign_lesson_plans=True, can_view_student_reports=True)
        self.client.login(username='otra', password='x')
        self.assertEqual(self.client.get(reverse('homework:task_report', args=[self.task.pk])).status_code, 404)

    def test_task_list_and_detail_link_to_report(self):
        self.client.login(username='duena', password='x')
        report_url = reverse('homework:task_report', args=[self.task.pk])
        self.assertContains(self.client.get(reverse('homework:task_list')), report_url)
        self.assertContains(self.client.get(reverse('homework:task_detail', args=[self.task.pk])), report_url)


class FamilyAndStudentViewTests(ReportTestCase):
    def test_parent_sees_only_completion(self):
        parent_user = self._user('papa', 'PARENT')
        ParentProfile.objects.create(user=parent_user, name='Papá').students.add(self.ana, self.beto)
        self.client.login(username='papa', password='x')
        response = self.client.get(reverse('dashboard:parents'))
        self.assertContains(response, 'terminó la tarea «Los animales»')
        self.assertContains(response, 'Celebren juntos')
        self.assertNotContains(response, 'Beto terminó')
        for text in ('leyeron', 'Aprendizaje', 'omisi'):
            self.assertNotContains(response, text)

    def test_student_never_sees_levels(self):
        self.client.login(username='ana', password='x')
        response = self.client.get(reverse('homework:student_task', args=[self.assignment.pk]))
        self.assertNotContains(response, 'Aprendizaje')

    def test_student_report_links_tasks_only_with_difficulty_permission(self):
        url = reverse('dashboard:student_report', args=[self.ana.pk])
        self.client.login(username='duena', password='x')
        self.assertContains(self.client.get(url), self.url)
        ParentProfile.objects.create(user=self._user('papa', 'PARENT'), name='Papá').students.add(self.ana)
        self.client.login(username='papa', password='x')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.url)


class DifficultyPermissionTests(ReportTestCase):
    def test_false_for_parent_student_and_unlinked_staff_and_never_raises(self):
        parent_user = self._user('papa', 'PARENT')
        ParentProfile.objects.create(user=parent_user, name='Papá').students.add(self.ana)
        self.assertFalse(can_view_difficulty_data(parent_user, self.ana))
        self.assertFalse(can_view_difficulty_data(self.ana.user, self.ana))
        staff = self._user('staff1', 'TEACHER')
        staff.is_staff = True
        staff.save()
        self.assertFalse(can_view_difficulty_data(staff, self.ana))
        admin = self._user('admin1', 'ADMIN')
        self.assertTrue(can_view_difficulty_data(admin, self.ana))
