from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from learning.models import TeacherProfile


class DashboardProfileGuardTests(TestCase):
    def test_student_without_profile_is_redirected_to_profile(self):
        user = CustomUser.objects.create_user(
            username='sinperfil',
            email='sinperfil@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:student'))

        self.assertRedirects(response, reverse('accounts:profile'))


class AdminResourceDeleteTests(TestCase):
    def test_admin_sidebar_is_visible_on_resource_pages(self):
        admin = CustomUser.objects.create_user(
            username='adminmenu',
            email='adminmenu@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        list_response = self.client.get(reverse('dashboard:admin_resource', args=['profesores']))
        create_response = self.client.get(reverse('dashboard:admin_resource_create', args=['profesores']))

        self.assertContains(list_response, 'Panel de control')
        self.assertContains(list_response, 'Docentes y permisos')
        self.assertContains(create_response, 'Panel de control')
        self.assertContains(create_response, 'Docentes y permisos')

    def test_superusers_are_hidden_from_user_resource_list(self):
        admin = CustomUser.objects.create_user(
            username='adminlista',
            email='adminlista@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        superuser = CustomUser.objects.create_superuser(
            username='superoculto',
            email='superoculto@example.com',
            password='Admin12345!',
        )
        regular_user = CustomUser.objects.create_user(
            username='usuariovisible',
            email='usuariovisible@example.com',
            password='Demo12345!',
            role=CustomUser.Role.PARENT,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard:admin_resource', args=['usuarios']))

        self.assertContains(response, regular_user.username)
        self.assertNotContains(response, superuser.username)

    def test_admin_create_dialogs_are_rendered(self):
        admin = CustomUser.objects.create_user(
            username='admindialogos',
            email='admindialogos@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        for resource in ('usuarios', 'profesores', 'alumnos'):
            response = self.client.get(reverse('dashboard:admin_resource', args=[resource]))
            self.assertContains(response, 'createResourceModal')

        plans_response = self.client.get(reverse('dashboard:lesson_plans'))
        self.assertContains(plans_response, 'createLessonPlanModal')

    def test_educational_resources_create_dialogs_are_rendered(self):
        admin = CustomUser.objects.create_user(
            username='adminrecursosdialogos',
            email='adminrecursosdialogos@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        for resource in ('niveles', 'estrategias', 'competencias', 'metodo-fas', 'referencias-mined', 'actividades', 'juegos', 'lecturas', 'palabras', 'silabas'):
            response = self.client.get(reverse('dashboard:admin_resource', args=[resource]))
            self.assertContains(response, 'createResourceModal')
            self.assertContains(response, f'Agregar')

    def test_admin_edit_dialog_is_rendered_for_users_and_preserves_password(self):
        admin = CustomUser.objects.create_user(
            username='admineditdialog',
            email='admineditdialog@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        user = CustomUser.objects.create_user(
            username='usuarioeditar',
            email='usuarioeditar@example.com',
            password='Demo12345!',
            role=CustomUser.Role.PARENT,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard:admin_resource', args=['usuarios']))
        self.assertContains(response, f'editResourceModal{user.pk}')

        update_response = self.client.post(reverse('dashboard:admin_resource_update', args=['usuarios', user.pk]), data={
            'username': 'usuarioeditado',
            'email': 'usuarioeditado@example.com',
            'first_name': 'Usuario',
            'last_name': 'Editado',
            'role': CustomUser.Role.PARENT,
            'is_active': 'on',
        })

        self.assertRedirects(update_response, reverse('dashboard:admin_resource', args=['usuarios']))
        user.refresh_from_db()
        self.assertEqual(user.username, 'usuarioeditado')
        self.assertTrue(user.check_password('Demo12345!'))

    def test_teacher_permissions_dialog_is_rendered_and_updates_permissions(self):
        admin = CustomUser.objects.create_user(
            username='adminpermisos',
            email='adminpermisos@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        teacher_user = CustomUser.objects.create_user(
            username='docentepermisos',
            email='docentepermisos@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Permisos')
        self.client.force_login(admin)

        list_response = self.client.get(reverse('dashboard:admin_resource', args=['profesores']))
        self.assertContains(list_response, f'permissionsModal{teacher.pk}')
        self.assertContains(list_response, 'Permisos del usuario')

        update_response = self.client.post(reverse('dashboard:teacher_permissions_update', args=[teacher.pk]), data={
            'can_manage_lessons': 'on',
            'can_manage_readings': 'on',
        })

        self.assertRedirects(update_response, reverse('dashboard:admin_resource', args=['profesores']))
        teacher.refresh_from_db()
        self.assertTrue(teacher.can_manage_lessons)
        self.assertFalse(teacher.can_manage_activities)
        self.assertTrue(teacher.can_manage_readings)

    def test_admin_can_delete_teacher_profile_without_user(self):
        admin = CustomUser.objects.create_user(
            username='adminborrar',
            email='adminborrar@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        teacher = TeacherProfile.objects.create(first_name='Docente', last_name='Borrar', email='docenteborrar@example.com', name='Docente Borrar')
        self.client.force_login(admin)

        response = self.client.post(reverse('dashboard:admin_resource_delete', args=['profesores', teacher.pk]))

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['profesores']))
        self.assertFalse(TeacherProfile.objects.filter(pk=teacher.pk).exists())

    def test_admin_cannot_delete_self(self):
        admin = CustomUser.objects.create_user(
            username='adminpropio',
            email='adminpropio@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.post(reverse('dashboard:admin_resource_delete', args=['usuarios', admin.pk]))

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['usuarios']))
        self.assertTrue(CustomUser.objects.filter(pk=admin.pk).exists())

    def test_parent_without_profile_is_redirected_to_profile(self):
        user = CustomUser.objects.create_user(
            username='padresinperfil',
            email='padresinperfil@example.com',
            password='Demo12345!',
            role=CustomUser.Role.PARENT,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:parents'))

        self.assertRedirects(response, reverse('accounts:profile'))
