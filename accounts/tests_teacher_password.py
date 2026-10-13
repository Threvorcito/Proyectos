from django.contrib.auth import authenticate
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from dashboard.forms import TeacherUpdateForm
from learning.models import TeacherProfile


class TeacherSinglePasswordTests(TestCase):
    def make_teacher(self, profile_password, user_password=None):
        user = CustomUser.objects.create_user(
            username='docente',
            email='docente@example.com',
            password=user_password,
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile(user=user, first_name='Ana', last_name='Ruiz', email='docente@example.com')
        teacher.set_password(profile_password)
        teacher.save()
        return user, teacher

    def test_legacy_profile_password_migrates_to_user(self):
        user, teacher = self.make_teacher('Legacy123!')

        self.assertEqual(authenticate(username='docente@example.com', password='Legacy123!'), user)

        user.refresh_from_db()
        teacher.refresh_from_db()
        self.assertTrue(user.check_password('Legacy123!'))
        self.assertEqual(teacher.password, '')

    def test_profile_password_ignored_when_user_has_usable_password(self):
        self.make_teacher('Viejo123!', user_password='Actual123!')

        self.assertIsNone(authenticate(username='docente@example.com', password='Viejo123!'))
        self.assertIsNotNone(authenticate(username='docente@example.com', password='Actual123!'))

    def test_admin_password_reset_invalidates_old_profile_password(self):
        user, teacher = self.make_teacher('Viejo123!')
        admin = CustomUser.objects.create_user(
            username='adminreset', email='adminreset@example.com', password='Admin12345!',
            role=CustomUser.Role.ADMIN, is_staff=True,
        )
        self.client.force_login(admin)

        self.client.post(reverse('dashboard:admin_resource_update', args=['usuarios', user.pk]), data={
            'username': 'docente',
            'email': 'docente@example.com',
            'first_name': 'Ana',
            'last_name': 'Ruiz',
            'role': CustomUser.Role.TEACHER,
            'is_active': 'on',
            'password': 'Nueva-Clave-2026',
        })

        teacher.refresh_from_db()
        self.assertEqual(teacher.password, '')
        self.assertIsNone(authenticate(username='docente@example.com', password='Viejo123!'))
        self.assertIsNotNone(authenticate(username='docente@example.com', password='Nueva-Clave-2026'))

    def test_teacher_update_form_writes_linked_user_password(self):
        user, teacher = self.make_teacher('Viejo123!', user_password='Actual123!')
        form = TeacherUpdateForm(instance=teacher, data={
            'first_name': 'Ana',
            'last_name': 'Ruiz',
            'email': 'docente@example.com',
            'password': 'Nueva123!',
            'is_active': 'on',
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        user.refresh_from_db()
        teacher.refresh_from_db()
        self.assertTrue(user.check_password('Nueva123!'))
        self.assertEqual(teacher.password, '')
