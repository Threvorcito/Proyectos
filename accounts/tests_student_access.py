"""Grade-1 student sign-in: classroom code -> card -> two drawings (order free)."""
from datetime import timedelta
from unittest import mock

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from core.models import AuditLog
from learning.models import Level, ParentProfile, StudentProfile, TeacherProfile

from . import lockout
from .models import CustomUser


def make_user(username, role, password='Clave12345!'):
    return CustomUser.objects.create_user(username=username, email=f'{username}@example.com', password=password, role=role)


class StudentAccessBase(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.teacher_user = make_user('maestra', CustomUser.Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, name='Maestra Ana', is_active=True)
        self.student_user = make_user('nino', CustomUser.Role.STUDENT, password='2468')
        self.student = StudentProfile.objects.create(
            user=self.student_user, name='Nino Pareja', grade='1', reading_level=self.level, current_level=self.level,
        )
        self.student.set_visual_key(['dog', 'cat'])
        self.student.save(update_fields=['visual_key_hash', 'visual_key_version'])
        self.teacher.students.add(self.student)

    def client_at_cards(self):
        client = Client()
        client.post(reverse('accounts:student_access'), {'code': self.teacher.classroom_code})
        return client

    def client_at_key(self):
        client = self.client_at_cards()
        client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})
        return client

    def try_pair(self, symbols):
        client = self.client_at_key()
        response = client.post(reverse('accounts:student_access_key'), {'symbols': symbols})
        return client, response


class StudentAccessFlowTests(StudentAccessBase):
    def test_student_without_tutor_signs_in(self):
        self.assertFalse(ParentProfile.objects.filter(students=self.student).exists())
        client, response = self.try_pair(['dog', 'cat'])
        self.assertRedirects(response, reverse('dashboard:student'))
        self.assertEqual(int(client.session['_auth_user_id']), self.student_user.pk)

    def test_card_goes_straight_to_drawings(self):
        client = self.client_at_cards()
        response = client.post(reverse('accounts:student_access_students'), {'student_id': self.student.pk})
        self.assertRedirects(response, reverse('accounts:student_access_key'))
        page = client.get(reverse('accounts:student_access_key'))
        self.assertNotContains(page, 'tutor')
        self.assertContains(page, 'name="symbols"', count=len(StudentProfile.VISUAL_KEY_CHOICES))

    def test_old_tutor_url_redirects_without_tutor_step(self):
        client = self.client_at_key()
        response = client.get(reverse('accounts:student_access_parents'))
        self.assertRedirects(response, reverse('accounts:student_access_key'))

    def test_pair_is_accepted_in_either_order(self):
        client, response = self.try_pair(['cat', 'dog'])
        self.assertIn('_auth_user_id', client.session)
        client, response = self.try_pair(['dog', 'cat'])
        self.assertIn('_auth_user_id', client.session)

    def test_wrong_pair_is_rejected_kindly(self):
        client, response = self.try_pair(['dog', 'sun'])
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', client.session)
        self.assertContains(response, 'Casi')
        self.assertNotContains(response, 'alert-danger')

    def test_one_or_three_drawings_are_rejected(self):
        for symbols in (['dog'], ['dog', 'cat', 'sun'], ['dog', 'dog']):
            client, _ = self.try_pair(symbols)
            self.assertNotIn('_auth_user_id', client.session)

    def test_classroom_code_still_required_before_roster_and_key(self):
        client = Client()
        self.assertRedirects(client.get(reverse('accounts:student_access_students')), reverse('accounts:student_access'))
        response = client.post(reverse('accounts:student_access_key'), {'symbols': ['dog', 'cat']})
        self.assertRedirects(response, reverse('accounts:student_access'))
        self.assertNotIn('_auth_user_id', client.session)

    def test_code_step_is_addressed_to_the_teacher(self):
        response = Client().get(reverse('accounts:student_access'))
        self.assertContains(response, 'Para la maestra o el maestro')


class LegacyVisualKeyTests(StudentAccessBase):
    def setUp(self):
        super().setUp()
        self.student.set_visual_key(['dog', 'star', 'car'])
        self.student.save(update_fields=['visual_key_hash', 'visual_key_version'])

    def test_legacy_three_ordered_drawings_still_work(self):
        self.assertEqual(self.student.visual_key_version, StudentProfile.VISUAL_KEY_LEGACY)
        client = self.client_at_key()
        page = client.get(reverse('accounts:student_access_key'))
        self.assertContains(page, 'symbol_3')
        response = client.post(reverse('accounts:student_access_key'), {'symbol_1': 'dog', 'symbol_2': 'star', 'symbol_3': 'car'})
        self.assertRedirects(response, reverse('dashboard:student'))

    def test_legacy_key_order_matters(self):
        client = self.client_at_key()
        client.post(reverse('accounts:student_access_key'), {'symbol_1': 'car', 'symbol_2': 'star', 'symbol_3': 'dog'})
        self.assertNotIn('_auth_user_id', client.session)

    def test_regenerate_makes_a_pair_key_and_drops_the_old_one(self):
        with mock.patch('learning.models.secrets.SystemRandom.sample', return_value=['sun', 'fish']):
            items = self.student.generate_visual_key()
        self.student.refresh_from_db()
        self.assertEqual([item['label'] for item in items], ['sol', 'pez'])
        self.assertEqual(self.student.visual_key_version, StudentProfile.VISUAL_KEY_PAIR)
        self.assertFalse(self.student.check_visual_key(['dog', 'star', 'car']))
        self.assertTrue(self.student.check_visual_key(['fish', 'sun']))


class ProgressiveLockTests(StudentAccessBase):
    def fail_until_locked(self, at):
        with mock.patch('accounts.lockout._now', return_value=at):
            for _ in range(lockout.MAX_FAILURES):
                self.try_pair(['sun', 'fish'])

    def test_five_failures_lock_for_a_while(self):
        start = timezone.now()
        self.fail_until_locked(start)
        with mock.patch('accounts.lockout._now', return_value=start):
            client, response = self.try_pair(['dog', 'cat'])
        self.assertNotIn('_auth_user_id', client.session)
        self.assertContains(client.get(response.url), 'Pide ayuda a tu maestra')
        with mock.patch('accounts.lockout._now', return_value=start + timedelta(minutes=16)):
            client, _ = self.try_pair(['dog', 'cat'])
        self.assertIn('_auth_user_id', client.session)

    def lock_three_times(self):
        start = timezone.now()
        for round_number in range(3):
            self.fail_until_locked(start + timedelta(minutes=20 * round_number))
        return start + timedelta(minutes=60)

    def test_three_lockouts_in_a_day_need_the_teacher(self):
        later = self.lock_three_times()
        key = lockout.student_key(self.student.pk)
        with mock.patch('accounts.lockout._now', return_value=later + timedelta(hours=5)):
            self.assertTrue(lockout.needs_unlock(key))
            client, _ = self.try_pair(['dog', 'cat'])
        self.assertNotIn('_auth_user_id', client.session)

    def test_lockouts_spread_over_more_than_a_day_do_not_escalate(self):
        start = timezone.now()
        for round_number in range(3):
            self.fail_until_locked(start + timedelta(hours=13 * round_number))
        self.assertFalse(lockout.needs_unlock(lockout.student_key(self.student.pk)))

    def test_teacher_unlocks_own_student_with_audit(self):
        self.lock_three_times()
        self.client.force_login(self.teacher_user)
        students_page = self.client.get(reverse('dashboard:teacher_students'))
        self.assertContains(students_page, 'Desbloquear')
        response = self.client.post(reverse('dashboard:teacher_student_access_unlock', args=[self.student.pk]))
        self.assertRedirects(response, reverse('dashboard:teacher_students'), fetch_redirect_response=False)
        self.assertFalse(lockout.is_locked(lockout.student_key(self.student.pk)))
        self.assertTrue(AuditLog.objects.filter(action='unlock_student_access', object_id=str(self.student.pk)).exists())
        client, _ = self.try_pair(['dog', 'cat'])
        self.assertIn('_auth_user_id', client.session)

    def test_other_teacher_cannot_unlock(self):
        self.lock_three_times()
        other = TeacherProfile.objects.create(user=make_user('otra', CustomUser.Role.TEACHER), name='Otra', is_active=True)
        self.client.force_login(other.user)
        self.client.post(reverse('dashboard:teacher_student_access_unlock', args=[self.student.pk]))
        self.assertTrue(lockout.needs_unlock(lockout.student_key(self.student.pk)))

    def test_student_or_anonymous_cannot_unlock(self):
        self.lock_three_times()
        url = reverse('dashboard:teacher_student_access_unlock', args=[self.student.pk])
        Client().post(url)
        student_client = Client()
        student_client.force_login(self.student_user)
        student_client.post(url)
        self.assertTrue(lockout.needs_unlock(lockout.student_key(self.student.pk)))

    def test_admin_can_unlock(self):
        self.lock_three_times()
        admin = make_user('jefa', CustomUser.Role.ADMIN)
        self.client.force_login(admin)
        self.client.post(reverse('dashboard:teacher_student_access_unlock', args=[self.student.pk]))
        self.assertFalse(lockout.is_locked(lockout.student_key(self.student.pk)))

    def test_new_key_also_unlocks(self):
        self.lock_three_times()
        self.client.force_login(self.teacher_user)
        self.client.post(reverse('dashboard:teacher_student_visual_key_regenerate', args=[self.student.pk]), {'had_visual_key': '1'})
        self.assertFalse(lockout.is_locked(lockout.student_key(self.student.pk)))
