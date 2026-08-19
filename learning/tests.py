from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class AccessibilitySettingsGuardTests(TestCase):
    def test_non_student_user_is_redirected_from_accessibility_settings(self):
        user = CustomUser.objects.create_user(
            username='docenteacceso',
            email='docenteacceso@example.com',
            password='Demo12345!',
            role=CustomUser.Role.TEACHER,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('learning:accessibility'))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
