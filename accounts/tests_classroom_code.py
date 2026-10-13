from django.test import Client, TestCase
from django.urls import reverse

from learning.models import Level, StudentProfile, TeacherProfile

from .models import CustomUser


class ClassroomCodeTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.teacher = self.make_teacher('ana', 'Profe Ana')
        self.other_teacher = self.make_teacher('beto', 'Profe Beto')
        self.make_student('sofia', 'Sofía Aula', self.teacher)
        self.make_student('mateo', 'Mateo Otro', self.other_teacher)

    def make_teacher(self, username, name):
        user = CustomUser.objects.create_user(
            username=username, email=f'{username}@example.com', password='Docente123!', role=CustomUser.Role.TEACHER,
        )
        return TeacherProfile.objects.create(user=user, name=name, is_active=True)

    def make_student(self, username, name, teacher):
        user = CustomUser.objects.create_user(
            username=username, email=f'{username}@example.com', password='2468', role=CustomUser.Role.STUDENT,
        )
        student = StudentProfile.objects.create(user=user, name=name, grade='1', reading_level=self.level, current_level=self.level)
        teacher.students.add(student)
        return student

    def test_teachers_get_unique_unambiguous_codes(self):
        self.assertEqual(len(self.teacher.classroom_code), 6)
        self.assertNotEqual(self.teacher.classroom_code, self.other_teacher.classroom_code)
        self.assertTrue(set(self.teacher.classroom_code) <= set(TeacherProfile.CLASSROOM_CODE_ALPHABET))

    def test_entry_page_lists_no_teacher_or_student(self):
        response = self.client.get(reverse('accounts:student_access'))

        self.assertEqual(response.status_code, 200)
        for name in ('Profe Ana', 'Profe Beto', 'Sofía Aula', 'Mateo Otro'):
            self.assertNotContains(response, name)
        self.assertContains(response, 'name="code"')

    def test_wrong_code_shows_error_without_names(self):
        response = self.client.post(reverse('accounts:student_access'), {'code': 'ZZZZZZ'}, follow=True)

        self.assertContains(response, 'Ese código no es correcto')
        self.assertNotContains(response, 'Sofía Aula')
        self.assertNotIn('student_access_teacher_id', self.client.session)

    def test_right_code_shows_only_that_teachers_students(self):
        response = self.client.post(
            reverse('accounts:student_access'), {'code': f' {self.teacher.classroom_code.lower()} '}, follow=True,
        )

        self.assertContains(response, 'Sofía Aula')
        self.assertNotContains(response, 'Mateo Otro')

    def test_teacher_id_without_code_is_ignored(self):
        self.client.post(reverse('accounts:student_access'), {'code': self.teacher.classroom_code})

        response = self.client.post(reverse('accounts:student_access'), {'teacher_id': self.other_teacher.pk})
        self.assertEqual(self.client.session['student_access_teacher_id'], self.teacher.pk)

        session = self.client.session
        session['student_access_teacher_id'] = self.other_teacher.pk
        session.save()
        response = self.client.get(reverse('accounts:student_access_students'))
        self.assertRedirects(response, reverse('accounts:student_access'), fetch_redirect_response=False)
        self.assertNotContains(self.client.get(reverse('accounts:student_access'), follow=True), 'Mateo Otro')

    def test_anonymous_students_page_redirects_to_code(self):
        response = self.client.get(reverse('accounts:student_access_students'))

        self.assertRedirects(response, reverse('accounts:student_access'))

    def test_device_remembers_classroom_with_signed_cookie(self):
        self.client.post(reverse('accounts:student_access'), {'code': self.teacher.classroom_code})
        cookie = self.client.cookies['classroom']

        device = Client()
        device.cookies['classroom'] = cookie.value
        response = device.get(reverse('accounts:student_access'), follow=True)
        self.assertContains(response, 'Sofía Aula')

        tampered = Client()
        tampered.cookies['classroom'] = cookie.value.replace(str(self.teacher.pk), str(self.other_teacher.pk), 1)
        response = tampered.get(reverse('accounts:student_access'), follow=True)
        self.assertNotContains(response, 'Mateo Otro')
        self.assertNotContains(response, 'Sofía Aula')

    def test_regenerated_code_invalidates_remembered_device(self):
        self.client.post(reverse('accounts:student_access'), {'code': self.teacher.classroom_code})
        self.teacher.regenerate_classroom_code()

        response = self.client.get(reverse('accounts:student_access_students'))
        self.assertRedirects(response, reverse('accounts:student_access'), fetch_redirect_response=False)
        self.assertNotContains(self.client.get(reverse('accounts:student_access')), 'Sofía Aula')

    def test_repeated_wrong_codes_lock_the_client(self):
        for _ in range(20):
            self.client.post(reverse('accounts:student_access'), {'code': 'ZZZZZZ'})

        response = self.client.post(reverse('accounts:student_access'), {'code': self.teacher.classroom_code}, follow=True)
        self.assertNotContains(response, 'Sofía Aula')
        self.assertContains(response, 'Pide ayuda a tu docente')

    def test_teacher_dashboard_shows_code_and_can_regenerate(self):
        self.client.force_login(self.teacher.user)

        response = self.client.get(reverse('dashboard:teacher'))
        self.assertContains(response, self.teacher.classroom_code)

        old_code = self.teacher.classroom_code
        self.client.post(reverse('dashboard:teacher_classroom_code_regenerate'))
        self.teacher.refresh_from_db()
        self.assertNotEqual(self.teacher.classroom_code, old_code)
