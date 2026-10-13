from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser


class AdminUserPrivilegeTests(TestCase):
    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='adminrole',
            email='adminrole@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.superuser = CustomUser.objects.create_superuser(
            username='root',
            email='root@example.com',
            password='Root12345!',
        )

    def create_payload(self, username, **extra):
        data = {
            'username': username,
            'email': f'{username}@example.com',
            'first_name': 'Nuevo',
            'last_name': 'Usuario',
            'role': CustomUser.Role.PARENT,
            'password1': 'Clave-Segura-2026',
            'password2': 'Clave-Segura-2026',
        }
        data.update(extra)
        return data

    def test_admin_role_cannot_create_superuser_or_staff(self):
        self.client.force_login(self.admin)

        self.client.post(
            reverse('dashboard:admin_resource_create', args=['usuarios']),
            data=self.create_payload('escalado', is_superuser='on', is_staff='on'),
        )

        created = CustomUser.objects.get(username='escalado')
        self.assertFalse(created.is_superuser)
        self.assertFalse(created.is_staff)

    def test_admin_role_cannot_grant_staff_on_update(self):
        target = CustomUser.objects.create_user(
            username='tutor', email='tutor@example.com', password='Demo12345!', role=CustomUser.Role.PARENT,
        )
        self.client.force_login(self.admin)

        self.client.post(reverse('dashboard:admin_resource_update', args=['usuarios', target.pk]), data={
            'username': 'tutor',
            'email': 'tutor@example.com',
            'first_name': 'Tutor',
            'last_name': 'Demo',
            'role': CustomUser.Role.PARENT,
            'is_active': 'on',
            'is_staff': 'on',
            'is_superuser': 'on',
        })

        target.refresh_from_db()
        self.assertFalse(target.is_staff)
        self.assertFalse(target.is_superuser)

    def test_superuser_can_grant_staff_but_not_superuser(self):
        self.client.force_login(self.superuser)

        self.client.post(
            reverse('dashboard:admin_resource_create', args=['usuarios']),
            data=self.create_payload('staffer', is_superuser='on', is_staff='on'),
        )

        created = CustomUser.objects.get(username='staffer')
        self.assertTrue(created.is_staff)
        self.assertFalse(created.is_superuser)
