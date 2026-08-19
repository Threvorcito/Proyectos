from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from dashboard.forms import TeacherCreationForm
from learning.models import TeacherProfile


class TeacherCreationFormTests(TestCase):
    def test_creates_independent_teacher_profile(self):
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
        teacher = form.save()

        self.assertIsNone(teacher.user)
        self.assertEqual(teacher.name, 'Maria Lopez')
        self.assertEqual(teacher.email, 'mlopez@example.com')
        self.assertTrue(teacher.check_password('Demo12345!'))
        self.assertFalse(CustomUser.objects.filter(email='mlopez@example.com').exists())

    def test_admin_panel_creates_independent_teacher_profile(self):
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

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['profesores']))
        teacher = TeacherProfile.objects.get(user__isnull=True, name='Carlos Rivera', email='crivera@example.com')
        self.assertTrue(teacher.check_password('Docente123!'))
        self.assertFalse(CustomUser.objects.filter(email='crivera@example.com').exists())
