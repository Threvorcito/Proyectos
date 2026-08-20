from django.test import TestCase
from django.urls import reverse

from .forms import ProfileUpdateForm
from learning.models import TeacherProfile

from .models import CustomUser


class LoginTests(TestCase):
    def test_user_can_login_with_email(self):
        CustomUser.objects.create_user(
            username='admincorreo',
            email='admincorreo@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )

        response = self.client.post(reverse('accounts:login'), data={
            'username': 'admincorreo@example.com',
            'password': 'Admin12345!',
        })

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)


class RegisterTests(TestCase):
    def test_new_teacher_account_is_created_and_logged_in(self):
        response = self.client.post(reverse('accounts:register'), data={
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'username': 'maria_lopez',
            'email': 'maria@example.com',
            'role': CustomUser.Role.TEACHER,
            'password1': 'Docente123!',
            'password2': 'Docente123!',
        })

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
        user = CustomUser.objects.get(username='maria_lopez')
        self.assertEqual(user.role, CustomUser.Role.TEACHER)
        self.assertEqual(user.email, 'maria@example.com')
        self.assertTrue(user.is_authenticated)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)


class ProfileUpdateFormTests(TestCase):
    def test_profile_form_includes_professional_fields(self):
        form = ProfileUpdateForm()

        self.assertIn('gender', form.fields)
        self.assertIn('profile_photo', form.fields)
        self.assertEqual(form.fields['gender'].label, 'Sexo')
        self.assertEqual(form.fields['profile_photo'].label, 'Foto de perfil')

    def test_teacher_profile_can_login_with_email(self):
        teacher = TeacherProfile.objects.create(
            first_name='Maria',
            last_name='Lopez',
            email='mlopez@example.com',
            name='Maria Lopez',
            can_manage_lessons=True,
        )
        teacher.set_password('Docente123!')
        teacher.save()

        response = self.client.post(reverse('accounts:login'), data={
            'username': 'mlopez@example.com',
            'password': 'Docente123!',
        })

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
        teacher.refresh_from_db()
        self.assertIsNotNone(teacher.user)
        self.assertEqual(teacher.user.role, CustomUser.Role.TEACHER)
        self.assertEqual(teacher.user.email, 'mlopez@example.com')

    def test_username_login_still_works(self):
        CustomUser.objects.create_user(
            username='usuarioexistente',
            email='usuarioexistente@example.com',
            password='Demo12345!',
        )

        response = self.client.post(reverse('accounts:login'), data={
            'username': 'usuarioexistente',
            'password': 'Demo12345!',
        })

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
