from django.test import TestCase
from django.urls import reverse

from .forms import ProfileUpdateForm
from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile

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
    def test_public_register_form_does_not_offer_teacher_role(self):
        response = self.client.get(reverse('accounts:register'))

        self.assertContains(response, 'Padre o tutor')
        self.assertNotContains(response, 'Docente')

    def test_new_parent_account_is_created_and_logged_in(self):
        response = self.client.post(reverse('accounts:register'), data={
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'username': 'maria_lopez',
            'email': 'maria@example.com',
            'role': CustomUser.Role.PARENT,
            'password1': 'Docente123!',
            'password2': 'Docente123!',
        })

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
        user = CustomUser.objects.get(username='maria_lopez')
        self.assertEqual(user.role, CustomUser.Role.PARENT)
        self.assertEqual(user.email, 'maria@example.com')
        self.assertTrue(user.is_authenticated)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_public_register_rejects_manipulated_teacher_role(self):
        response = self.client.post(reverse('accounts:register'), data={
            'first_name': 'Maria',
            'last_name': 'Lopez',
            'username': 'docente_manipulado',
            'email': 'docente_manipulado@example.com',
            'role': CustomUser.Role.TEACHER,
            'password1': 'Docente123!',
            'password2': 'Docente123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TEACHER no es una de las opciones disponibles.')
        self.assertFalse(CustomUser.objects.filter(username='docente_manipulado').exists())


class ProfileViewAccessTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")


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


class StudentVisualAccessTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.teacher_user = CustomUser.objects.create_user(
            username='docentevisual',
            email='docentevisual@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, name='Docente Visual', is_active=True)
        self.student_user = CustomUser.objects.create_user(
            username='alumnovisual',
            email='alumnovisual@example.com',
            password='2468',
            role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            name='Alumno Visual',
            grade='1',
            reading_level=self.level,
            current_level=self.level,
        )
        self.student.set_visual_key(['dog', 'star', 'car'])
        self.student.save(update_fields=['visual_key_hash'])
        self.teacher.students.add(self.student)
        self.parent_user = CustomUser.objects.create_user(
            username='tutorvisual',
            email='tutorvisual@example.com',
            password='Tutor12345!',
            role=CustomUser.Role.PARENT,
        )
        self.parent = ParentProfile.objects.create(user=self.parent_user, name='Tutor Visual')
        self.parent.students.add(self.student)

    def test_student_visual_access_logs_in_same_student_profile(self):
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})
        self.client.post(reverse('accounts:student_access_parents'), {'parent_id': self.parent.pk})

        response = self.client.post(reverse('accounts:student_access_key'), {
            'symbol_1': 'dog',
            'symbol_2': 'star',
            'symbol_3': 'car',
        })

        self.assertRedirects(response, reverse('dashboard:student'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.student_user.pk)

    def test_student_visual_access_rejects_student_not_linked_to_teacher(self):
        other_user = CustomUser.objects.create_user(username='otroalumno', email='otroalumno@example.com', password='2468', role=CustomUser.Role.STUDENT)
        other_student = StudentProfile.objects.create(user=other_user, name='Otro Alumno', grade='1', reading_level=self.level, current_level=self.level)
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})

        response = self.client.post(reverse('accounts:student_access_students'), {'student_id': other_student.pk})

        self.assertRedirects(response, reverse('accounts:student_access_students'))
        self.assertNotIn('student_access_student_id', self.client.session)

    def test_student_visual_access_rejects_parent_not_linked_to_student(self):
        other_parent_user = CustomUser.objects.create_user(username='otrotutor', email='otrotutor@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        other_parent = ParentProfile.objects.create(user=other_parent_user, name='Otro Tutor')
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})

        response = self.client.post(reverse('accounts:student_access_parents'), {'parent_id': other_parent.pk})

        self.assertRedirects(response, reverse('accounts:student_access_parents'))
        self.assertNotIn('student_access_parent_id', self.client.session)

    def test_student_visual_access_shows_linked_parent(self):
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})

        response = self.client.get(reverse('accounts:student_access_parents'))

        self.assertContains(response, 'Tutor Visual')
        self.assertNotContains(response, 'Falta vincular un tutor')

    def test_student_visual_access_shows_two_linked_parents(self):
        second_parent_user = CustomUser.objects.create_user(username='tutorvisualdos', email='tutorvisualdos@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        second_parent = ParentProfile.objects.create(user=second_parent_user, name='Tutor Visual Dos')
        second_parent.students.add(self.student)
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})

        response = self.client.get(reverse('accounts:student_access_parents'))

        self.assertContains(response, 'Tutor Visual')
        self.assertContains(response, 'Tutor Visual Dos')

    def test_student_visual_access_without_parent_shows_help_message(self):
        self.parent.students.remove(self.student)
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})

        response = self.client.get(reverse('accounts:student_access_parents'))

        self.assertContains(response, 'Falta vincular un tutor')

    def test_student_visual_access_rejects_wrong_visual_key(self):
        self.client.post(reverse('accounts:student_access'), {'teacher_id': self.teacher.pk})
        self.client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})
        self.client.post(reverse('accounts:student_access_parents'), {'parent_id': self.parent.pk})

        response = self.client.post(reverse('accounts:student_access_key'), {
            'symbol_1': 'car',
            'symbol_2': 'star',
            'symbol_3': 'dog',
        })

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
