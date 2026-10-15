import datetime

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import CustomUser
from learning.models import LessonPlan, Level, StudentProfile, Subject, TeacherProfile

from .models import Task, TaskAssignment


class TeacherTaskTestCase(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.other_subject = Subject.objects.create(name='Matemática')
        self.teacher = self._teacher('maestra', 'Maestra Ana', can_assign_lesson_plans=True)
        self.other_teacher = self._teacher('maestro2', 'Maestro Luis', can_assign_lesson_plans=True)
        self.ana = self._student('ana', 'Ana', '1')
        self.beto = self._student('beto', 'Beto', '1')
        self.carla = self._student('carla', 'Carla', '2')
        self.solo = self._student('solo', 'Solo', '1')
        self.teacher.students.add(self.ana, self.beto, self.carla)
        self.client.login(username='maestra', password='x')

    def _teacher(self, username, name, **flags):
        user = CustomUser.objects.create_user(username=username, password='x', role='TEACHER', email=f'{username}@example.com')
        return TeacherProfile.objects.create(user=user, name=name, is_active=True, **flags)

    def _student(self, username, name, grade):
        user = CustomUser.objects.create_user(username=username, password='x', role='STUDENT', email=f'{username}@example.com')
        return StudentProfile.objects.create(user=user, name=name, grade=grade, reading_level=self.level, current_level=self.level)

    def _task(self, **extra):
        data = {'teacher': self.teacher, 'subject': self.subject, 'grade': '1', 'title': 'Los animales'}
        data.update(extra)
        return Task.objects.create(**data)

    def _plan(self, teacher, **extra):
        data = {'teacher': teacher, 'subject': self.other_subject, 'level': self.level, 'grade': '2', 'title': 'Plan', 'topic': 'Tema', 'objective': 'Objetivo'}
        data.update(extra)
        return LessonPlan.objects.create(**data)


class TaskPermissionTests(TeacherTaskTestCase):
    def test_task_list_requires_assign_permission(self):
        self.teacher.can_assign_lesson_plans = False
        self.teacher.save()
        response = self.client.get(reverse('homework:task_list'))
        self.assertRedirects(response, reverse('dashboard:teacher'), fetch_redirect_response=False)

    def test_admin_can_view_every_task_but_not_create(self):
        self._task()
        CustomUser.objects.create_user(username='admin1', password='x', role='ADMIN', email='admin1@example.com')
        self.client.login(username='admin1', password='x')
        response = self.client.get(reverse('homework:task_list'))
        self.assertContains(response, 'Los animales')
        response = self.client.get(reverse('homework:task_create'))
        self.assertRedirects(response, reverse('dashboard:teacher'), fetch_redirect_response=False)

    def test_other_teacher_gets_404_on_task_detail(self):
        task = self._task(teacher=self.other_teacher)
        self.assertEqual(self.client.get(reverse('homework:task_detail', args=[task.pk])).status_code, 404)

    def test_other_teacher_cannot_assign_or_archive(self):
        task = self._task(teacher=self.other_teacher)
        self.assertEqual(self.client.post(reverse('homework:task_assign', args=[task.pk]), {'whole_group': 'on'}).status_code, 404)
        self.assertEqual(self.client.post(reverse('homework:task_archive', args=[task.pk])).status_code, 404)
        task.refresh_from_db()
        self.assertTrue(task.is_active)


class TaskCreateEditTests(TeacherTaskTestCase):
    def test_create_task_sets_teacher_and_redirects_to_detail(self):
        response = self.client.post(reverse('homework:task_create'), {'title': 'Los animales', 'subject': self.subject.pk, 'grade': '1', 'due_date': '2026-10-20'})
        task = Task.objects.get()
        self.assertEqual(task.teacher, self.teacher)
        self.assertRedirects(response, reverse('homework:task_detail', args=[task.pk]))

    def test_lesson_plan_link_copies_subject_and_grade(self):
        plan = self._plan(self.teacher)
        self.client.post(reverse('homework:task_create'), {'title': 'Desde plan', 'subject': self.subject.pk, 'grade': '1', 'lesson_plan': plan.pk})
        task = Task.objects.get()
        self.assertEqual(task.lesson_plan, plan)
        self.assertEqual(task.subject, self.other_subject)
        self.assertEqual(task.grade, '2')

    def test_cannot_link_other_teachers_plan(self):
        plan = self._plan(self.other_teacher)
        response = self.client.post(reverse('homework:task_create'), {'title': 'X', 'subject': self.subject.pk, 'grade': '1', 'lesson_plan': plan.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn('lesson_plan', response.context['form'].errors)
        self.assertFalse(Task.objects.exists())

    def test_locked_task_update_changes_only_due_date(self):
        task = self._task(due_date=datetime.date(2026, 10, 20))
        TaskAssignment.objects.create(task=task, student=self.ana, started_at=timezone.now())
        response = self.client.post(reverse('homework:task_update', args=[task.pk]), {'title': 'Otro título', 'subject': self.other_subject.pk, 'grade': '2', 'due_date': '2026-11-01'})
        self.assertRedirects(response, reverse('homework:task_detail', args=[task.pk]))
        task.refresh_from_db()
        self.assertEqual(task.title, 'Los animales')
        self.assertEqual(task.grade, '1')
        self.assertEqual(task.due_date, datetime.date(2026, 11, 1))

    def test_unlocked_task_update_changes_everything(self):
        task = self._task()
        self.client.post(reverse('homework:task_update', args=[task.pk]), {'title': 'Nuevo', 'subject': self.subject.pk, 'grade': '2'})
        task.refresh_from_db()
        self.assertEqual((task.title, task.grade), ('Nuevo', '2'))


class TaskAssignTests(TeacherTaskTestCase):
    def test_whole_group_assigns_only_linked_students_of_task_grade(self):
        task = self._task()
        self.client.post(reverse('homework:task_assign', args=[task.pk]), {'whole_group': 'on'})
        self.assertEqual(set(task.assignments.values_list('student__name', flat=True)), {'Ana', 'Beto'})

    def test_assign_ignores_unlinked_student_ids(self):
        task = self._task()
        response = self.client.post(reverse('homework:task_assign', args=[task.pk]), {'students': [self.ana.pk, self.solo.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(task.assignments.exists())

    def test_assign_selected_students(self):
        task = self._task()
        self.client.post(reverse('homework:task_assign', args=[task.pk]), {'students': [self.beto.pk]})
        self.assertEqual(list(task.assignments.values_list('student__name', flat=True)), ['Beto'])

    def test_assign_twice_does_not_duplicate(self):
        task = self._task()
        url = reverse('homework:task_assign', args=[task.pk])
        self.client.post(url, {'whole_group': 'on'})
        self.client.post(url, {'whole_group': 'on'})
        self.assertEqual(task.assignments.count(), 2)

    def test_assign_requires_a_choice(self):
        task = self._task()
        self.client.post(reverse('homework:task_assign', args=[task.pk]), {})
        self.assertFalse(task.assignments.exists())


class TaskListTests(TeacherTaskTestCase):
    def test_archived_task_hidden_from_list(self):
        task = self._task()
        self.assertContains(self.client.get(reverse('homework:task_list')), 'Los animales')
        self.client.post(reverse('homework:task_archive', args=[task.pk]))
        task.refresh_from_db()
        self.assertFalse(task.is_active)
        self.assertNotContains(self.client.get(reverse('homework:task_list')), 'Los animales')

    def test_list_shows_progress_and_search(self):
        task = self._task()
        self._task(title='Otra cosa')
        TaskAssignment.objects.create(task=task, student=self.ana, status='completed')
        TaskAssignment.objects.create(task=task, student=self.beto)
        response = self.client.get(reverse('homework:task_list'), {'q': 'animales'})
        self.assertContains(response, '1/2 terminaron')
        self.assertNotContains(response, 'Otra cosa')

    def test_list_only_shows_own_tasks(self):
        self._task(teacher=self.other_teacher, title='Ajena')
        self.assertNotContains(self.client.get(reverse('homework:task_list')), 'Ajena')

    def test_empty_state_copy(self):
        self.assertContains(self.client.get(reverse('homework:task_list')), 'Aún no tienes tareas. Crea la primera con solo la parte que hace el niño.')
