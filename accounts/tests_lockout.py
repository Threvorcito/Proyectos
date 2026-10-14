from datetime import timedelta
from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile

from . import lockout
from .models import CustomUser

RIGHT_KEY = {'symbol_1': 'dog', 'symbol_2': 'star', 'symbol_3': 'car'}
WRONG_KEY = {'symbol_1': 'car', 'symbol_2': 'star', 'symbol_3': 'dog'}


class LockoutPolicyTests(TestCase):
    def test_five_failures_lock_and_success_resets(self):
        key = 'test:policy'
        for _ in range(4):
            lockout.register_failure(key)
        self.assertFalse(lockout.is_locked(key))
        lockout.reset(key)
        for _ in range(4):
            lockout.register_failure(key)
        self.assertFalse(lockout.is_locked(key))
        lockout.register_failure(key)
        self.assertTrue(lockout.is_locked(key))

    def test_failures_outside_window_do_not_accumulate(self):
        key = 'test:window'
        start = timezone.now()
        with mock.patch('accounts.lockout._now', return_value=start):
            for _ in range(4):
                lockout.register_failure(key)
        with mock.patch('accounts.lockout._now', return_value=start + timedelta(minutes=16)):
            lockout.register_failure(key)
            self.assertFalse(lockout.is_locked(key))


class StudentVisualKeyLockoutTests(TestCase):
    def setUp(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        teacher_user = CustomUser.objects.create_user(
            username='docentelock', email='docentelock@example.com', password='Docente123!', role=CustomUser.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Lock', is_active=True)
        self.student_user = CustomUser.objects.create_user(
            username='alumnolock', email='alumnolock@example.com', password='2468', role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user, name='Alumno Lock', grade='1', reading_level=level, current_level=level,
        )
        self.student.set_visual_key(['dog', 'star', 'car'])
        self.student.save(update_fields=['visual_key_hash'])
        self.teacher.students.add(self.student)
        parent_user = CustomUser.objects.create_user(
            username='tutorlock', email='tutorlock@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT,
        )
        self.parent = ParentProfile.objects.create(user=parent_user, name='Tutor Lock')
        self.parent.students.add(self.student)

    def fresh_client_at_key_step(self):
        client = Client()
        session = client.session
        session['student_access_teacher_id'] = self.teacher.pk
        session['student_access_classroom_code'] = self.teacher.classroom_code
        session['student_access_student_id'] = self.student.pk
        session.save()
        return client

    def try_key(self, data):
        client = self.fresh_client_at_key_step()
        response = client.post(reverse('accounts:student_access_key'), data)
        return client, response

    def test_wrong_keys_from_fresh_clients_lock_the_student(self):
        start = timezone.now()
        with mock.patch('accounts.lockout._now', return_value=start):
            for _ in range(5):
                self.try_key(WRONG_KEY)
            client, response = self.try_key(RIGHT_KEY)

        self.assertNotIn('_auth_user_id', client.session)
        self.assertEqual(response.status_code, 302)
        self.assertContains(client.get(response.url), 'Pide ayuda a tu maestra')

        with mock.patch('accounts.lockout._now', return_value=start + timedelta(minutes=16)):
            client, response = self.try_key(RIGHT_KEY)
        self.assertEqual(int(client.session['_auth_user_id']), self.student_user.pk)

    def test_success_resets_failure_counter(self):
        for _ in range(4):
            self.try_key(WRONG_KEY)
        client, _ = self.try_key(RIGHT_KEY)
        self.assertIn('_auth_user_id', client.session)
        for _ in range(4):
            self.try_key(WRONG_KEY)
        client, _ = self.try_key(RIGHT_KEY)
        self.assertEqual(int(client.session['_auth_user_id']), self.student_user.pk)


class PasswordLoginLockoutTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='alumnopin', email='alumnopin@example.com', password='2468', role=CustomUser.Role.STUDENT,
        )

    def login(self, username, password):
        client = Client()
        response = client.post(reverse('accounts:login'), {'username': username, 'password': password})
        return client, response

    def test_wrong_pins_lock_account_even_with_right_pin(self):
        start = timezone.now()
        with mock.patch('accounts.lockout._now', return_value=start):
            for attempt in range(5):
                # Mixing case and email must not bypass the per-account counter.
                identifier = 'ALUMNOPIN' if attempt % 2 else 'alumnopin@example.com'
                self.login(identifier, '0000')
            client, response = self.login('alumnopin', '2468')

        self.assertNotIn('_auth_user_id', client.session)
        self.assertContains(response, 'bloqueada')

        with mock.patch('accounts.lockout._now', return_value=start + timedelta(minutes=16)):
            client, response = self.login('alumnopin', '2468')
        self.assertEqual(int(client.session['_auth_user_id']), self.user.pk)

    def test_success_resets_failure_counter(self):
        for _ in range(4):
            self.login('alumnopin', '0000')
        client, _ = self.login('alumnopin', '2468')
        self.assertIn('_auth_user_id', client.session)
        for _ in range(4):
            self.login('alumnopin', '0000')
        client, _ = self.login('alumnopin', '2468')
        self.assertEqual(int(client.session['_auth_user_id']), self.user.pk)

    def test_unknown_username_is_also_rate_limited(self):
        for _ in range(5):
            self.login('nadie', 'x')
        self.assertTrue(lockout.is_locked(lockout.password_login_key('nadie')))
