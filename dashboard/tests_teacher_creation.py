from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from dashboard.forms import TeacherCreationForm
from learning.models import TeacherProfile


class TeacherCreationFormTests(TestCase):
    def test_creates_teacher_user_and_profile(self):
        form = TeacherCreationForm(data={
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'email': 'mlopez@example.com',
            'password': 'Demo12345!',
            'can_manage_lessons': 'on',
            'can_manage_activities': 'on',
            'can_manage_readings': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()

        self.assertEqual(user.role, CustomUser.Role.TEACHER)
        self.assertEqual(user.username, 'mlopez@example.com')
        self.assertTrue(user.check_password('Demo12345!'))
        self.assertTrue(TeacherProfile.objects.filter(user=user, name='Maria Lopez').exists())

    def test_admin_panel_creates_teacher_user_and_profile(self):
        admin = CustomUser.objects.create_user(
            username='adminpanel',
            email='adminpanel@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.post(reverse('dashboard:admin_resource_create', args=['profesores']), data={
            'first_name': 'Carlos',
            'last_name': 'Rivera',
            'email': 'crivera@example.com',
            'password': 'Docente123!',
            'can_manage_lessons': 'on',
            'can_manage_activities': 'on',
            'can_manage_readings': 'on',
        })

        self.assertEqual(response.status_code, 200)
        teacher_user = CustomUser.objects.get(username='crivera@example.com')
        self.assertEqual(teacher_user.role, CustomUser.Role.TEACHER)
        self.assertTrue(teacher_user.check_password('Docente123!'))
        self.assertTrue(TeacherProfile.objects.filter(user=teacher_user, name='Carlos Rivera').exists())
        self.assertContains(response, 'Usuario creado para iniciar sesión')
