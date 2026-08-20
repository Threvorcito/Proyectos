from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from dashboard.forms import TeacherCreationForm, TeacherUpdateForm
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

    def test_teacher_update_form_can_change_password(self):
        teacher = TeacherProfile.objects.create(first_name='Ana', last_name='Ruiz', email='ana@example.com', name='Ana Ruiz')
        teacher.set_password('Anterior123!')
        teacher.save()

        form = TeacherUpdateForm(instance=teacher, data={
            'first_name': 'Ana',
            'last_name': 'Ruiz',
            'email': 'ana@example.com',
            'password': 'Nueva123!',
            'bio': 'Docente de primaria',
            'can_manage_lessons': 'on',
        })

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()

        self.assertTrue(updated.check_password('Nueva123!'))
        self.assertTrue(updated.can_manage_lessons)

    def test_teacher_update_form_preserves_password_when_empty(self):
        teacher = TeacherProfile.objects.create(first_name='Luis', last_name='Mora', email='luis@example.com', name='Luis Mora')
        teacher.set_password('Actual123!')
        teacher.save()

        form = TeacherUpdateForm(instance=teacher, data={
            'first_name': 'Luis',
            'last_name': 'Mora',
            'email': 'luis@example.com',
            'password': '',
            'bio': '',
        })

        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()

        self.assertTrue(updated.check_password('Actual123!'))

    def test_teacher_update_password_field_renders_empty(self):
        teacher = TeacherProfile.objects.create(first_name='Eva', last_name='Rios', email='eva@example.com', name='Eva Rios')
        teacher.set_password('Actual123!')
        teacher.save()

        form = TeacherUpdateForm(instance=teacher)

        self.assertEqual(form.fields['password'].initial, '')
        self.assertNotIn('value=', form['password'].as_widget())
