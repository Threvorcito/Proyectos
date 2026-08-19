from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class ProgressProfileGuardTests(TestCase):
    def test_non_student_user_is_redirected_to_profile(self):
        user = CustomUser.objects.create_user(
            username='docente',
            email='docente@example.com',
            password='Demo12345!',
            role=CustomUser.Role.TEACHER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('progress:overview'))

        self.assertRedirects(response, reverse('accounts:profile'))
