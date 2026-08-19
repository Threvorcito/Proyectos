from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from dashboard.forms import QuickStudentCreationForm
from activities.models import Activity
from games.models import Game
from learning.models import LessonPlan, LessonPlanAssignment, Level, StudentProfile, Subject, TeacherProfile


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


class QuickStudentCreationFormTests(TestCase):
    def test_teacher_form_does_not_ask_for_login_credentials(self):
        Level.objects.create(number=1, name='Inicial', order=1)

        form = QuickStudentCreationForm()

        self.assertNotIn('username', form.fields)
        self.assertNotIn('password', form.fields)

    def test_teacher_form_generates_student_credentials(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        form = QuickStudentCreationForm(data={
            'name': 'Sofia Perez',
            'alias': 'Sofi',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': level.pk,
        })

        self.assertTrue(form.is_valid(), form.errors)
        user, password = form.save()

        self.assertEqual(user.username, 'sofia_perez')
        self.assertEqual(user.email, 'sofia_perez@estudiante.local')
        self.assertEqual(user.role, CustomUser.Role.STUDENT)
        self.assertEqual(user.student_profile.school, 'public')
        self.assertEqual(len(password), 8)
        self.assertTrue(user.check_password(password))


class LessonPlanImplementationTests(TestCase):
    def test_teacher_can_open_own_plan_implementation(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        user = CustomUser.objects.create_user(
            username='docenteimplementa',
            email='docenteimplementa@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=user, name='Docente Implementa')
        plan = LessonPlan.objects.create(
            teacher=teacher,
            subject=subject,
            level=level,
            grade='1',
            title='Uso de y',
            topic='Ortografía',
            objective='Reconocer el uso de la y.',
            achievement_indicator='Reconoce reglas ortográficas en textos breves.',
        )
        Activity.objects.create(level=level, subject=subject, grade='1', title='Selecciona palabras con y', activity_type=Activity.ActivityType.SYLLABLES)
        Game.objects.create(level=level, subject=subject, grade='1', name='Detective de letras', slug='detective-letras', description='Juego de apoyo', skill='Discriminación visual')
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:lesson_plan_implementation', args=[plan.pk]))

        self.assertContains(response, 'Implementación del plan')
        self.assertContains(response, 'Reconoce reglas ortográficas en textos breves.')
        self.assertContains(response, 'Selecciona palabras con y')
        self.assertContains(response, 'Detective de letras')

    def test_assigned_plan_appears_in_student_dashboard(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        teacher_user = CustomUser.objects.create_user(username='docenteplan', email='docenteplan@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Plan')
        student_user = CustomUser.objects.create_user(username='sofia', email='sofia@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Sofia Perez', grade='1', reading_level=level, current_level=level)
        plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Lectura con apoyo', topic='Comprensión', objective='Comprender textos breves.')
        LessonPlanAssignment.objects.create(plan=plan, student=student)
        self.client.force_login(student_user)

        dashboard_response = self.client.get(reverse('dashboard:student'))
        plan_response = self.client.get(reverse('dashboard:student_lesson_plan', args=[plan.pk]))

        self.assertContains(dashboard_response, 'Mi clase de hoy')
        self.assertContains(dashboard_response, 'Lectura con apoyo')
        self.assertContains(plan_response, 'Mi clase con apoyo')
        self.assertContains(plan_response, 'Vamos paso a paso')


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
