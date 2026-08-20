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
        teacher = TeacherProfile.objects.create(user=user, name='Docente Implementa', can_assign_lesson_plans=True)
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

    def test_teacher_can_update_assignment_status_from_plan_report(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        user = CustomUser.objects.create_user(
            username='docentereporte',
            email='docentereporte@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=user, name='Docente Reporte', can_assign_lesson_plans=True)
        student_user = CustomUser.objects.create_user(username='alumnoreporte', email='alumnoreporte@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Reporte', grade='1', reading_level=level, current_level=level)
        plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Plan con reporte', topic='Comprensión', objective='Dar seguimiento.')
        assignment = LessonPlanAssignment.objects.create(plan=plan, student=student)
        self.client.force_login(user)

        report_response = self.client.get(reverse('dashboard:lesson_plan_report', args=[plan.pk]))
        update_response = self.client.post(reverse('dashboard:lesson_plan_assignment_update', args=[plan.pk, assignment.pk]), {
            'status': LessonPlanAssignment.Status.COMPLETED,
            'teacher_notes': 'Completó con lectura acompañada.',
        })
        assignment.refresh_from_db()

        self.assertContains(report_response, 'Reporte académico del plan')
        self.assertRedirects(update_response, reverse('dashboard:lesson_plan_report', args=[plan.pk]))
        self.assertEqual(assignment.status, LessonPlanAssignment.Status.COMPLETED)
        self.assertIsNotNone(assignment.completed_at)
        self.assertEqual(assignment.teacher_notes, 'Completó con lectura acompañada.')

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


class TeacherPermissionEnforcementTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.user = CustomUser.objects.create_user(
            username='docentesinpermisos',
            email='docentesinpermisos@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.user,
            name='Docente Sin Permisos',
            can_manage_lessons=False,
            can_manage_activities=False,
            can_manage_readings=False,
        )
        self.plan = LessonPlan.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            level=self.level,
            grade='1',
            title='Plan bloqueado',
            topic='Permisos',
            objective='Validar permisos.',
        )
        self.client.force_login(self.user)

    def test_teacher_without_lesson_permission_cannot_manage_plans(self):
        for route in (
            reverse('dashboard:lesson_plans'),
            reverse('dashboard:lesson_plan_create'),
            reverse('dashboard:lesson_plan_update', args=[self.plan.pk]),
            reverse('dashboard:lesson_plan_implementation', args=[self.plan.pk]),
            reverse('dashboard:lesson_plan_report', args=[self.plan.pk]),
        ):
            response = self.client.get(route)
            self.assertRedirects(response, reverse('dashboard:teacher'))

    def test_teacher_without_resource_permissions_cannot_manage_resources(self):
        for resource in ('clases', 'actividades', 'lecturas'):
            response = self.client.get(reverse('dashboard:admin_resource', args=[resource]))
            self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)

    def test_teacher_with_lesson_permission_can_open_plans(self):
        self.teacher.can_edit_lesson_plans = True
        self.teacher.save(update_fields=['can_edit_lesson_plans'])

        response = self.client.get(reverse('dashboard:lesson_plans'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Plan bloqueado')

    def test_profile_hides_management_options_without_permissions(self):
        response = self.client.get(reverse('accounts:profile'))

        self.assertContains(response, 'No tienes permisos de gestión académica activos.')
        self.assertNotContains(response, 'Agregar plan')
        self.assertNotContains(response, 'Planes que has creado')
        self.assertNotContains(response, 'Actividades recientes')
        self.assertNotContains(response, 'Lecturas activas')


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

    def test_admin_topbar_has_logout_menu(self):
        admin = CustomUser.objects.create_user(
            username='admintopbar',
            email='admintopbar@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard:admin'))

        self.assertContains(response, 'Cerrar sesión')
        self.assertContains(response, 'Mi forma de leer')

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

    def test_user_delete_removes_account_and_reactivation_restores_teacher_profile(self):
        admin = CustomUser.objects.create_user(
            username='adminsoftdelete',
            email='adminsoftdelete@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        teacher_user = CustomUser.objects.create_user(
            username='docentesoftdelete',
            email='docentesoftdelete@example.com',
            password='Docente123!',
            first_name='Docente',
            last_name='Restaurable',
            role=CustomUser.Role.TEACHER,
        )
        TeacherProfile.objects.create(user=teacher_user, name='Docente Restaurable', email=teacher_user.email)
        self.client.force_login(admin)

        delete_response = self.client.post(reverse('dashboard:admin_resource_delete', args=['usuarios', teacher_user.pk]))

        self.assertRedirects(delete_response, reverse('dashboard:admin_resource', args=['usuarios']))
        self.assertFalse(CustomUser.objects.filter(pk=teacher_user.pk).exists())

    def test_reactivating_orphan_teacher_user_restores_teacher_profile(self):
        admin = CustomUser.objects.create_user(
            username='adminrestoreteacher',
            email='adminrestoreteacher@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        teacher_user = CustomUser.objects.create_user(
            username='docenterestore',
            email='docenterestore@example.com',
            password='Docente123!',
            first_name='Docente',
            last_name='Restaurado',
            role=CustomUser.Role.TEACHER,
            is_active=False,
        )
        self.client.force_login(admin)

        restore_response = self.client.post(reverse('dashboard:admin_resource_update', args=['usuarios', teacher_user.pk]), data={
            'username': teacher_user.username,
            'email': teacher_user.email,
            'first_name': teacher_user.first_name,
            'last_name': teacher_user.last_name,
            'role': CustomUser.Role.TEACHER,
            'is_active': 'on',
        })
        teacher_user.refresh_from_db()

        self.assertRedirects(restore_response, reverse('dashboard:admin_resource', args=['usuarios']))
        self.assertTrue(teacher_user.is_active)
        self.assertTrue(TeacherProfile.objects.filter(user=teacher_user, email=teacher_user.email).exists())

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
        self.assertContains(list_response, f'editResourceModal{teacher.pk}')
        self.assertContains(list_response, 'Permisos del usuario')
        self.assertContains(list_response, 'Permisos del docente')
        self.assertContains(list_response, 'Recursos educativos')
        self.assertContains(list_response, 'Crear estudiantes')
        self.assertContains(list_response, 'Crear planes')
        self.assertContains(list_response, 'Gestionar actividades')
        self.assertContains(list_response, 'Gestionar lecturas')
        self.assertContains(list_response, 'Gestionar juegos')
        self.assertNotContains(list_response, 'Editar cuentos')
        self.assertNotContains(list_response, 'Organizar por materia')

        update_response = self.client.post(reverse('dashboard:teacher_permissions_update', args=[teacher.pk]), data={
            'can_create_lesson_plans': 'on',
            'can_manage_readings': 'on',
        })

        self.assertRedirects(update_response, reverse('dashboard:admin_resource', args=['profesores']))
        teacher.refresh_from_db()
        self.assertTrue(teacher.can_create_lesson_plans)
        self.assertFalse(teacher.can_manage_activities)
        self.assertTrue(teacher.can_manage_readings)

    def test_teacher_delete_deactivates_profile_and_preserves_lesson_plans(self):
        admin = CustomUser.objects.create_user(
            username='adminarchivadocente',
            email='adminarchivadocente@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        teacher_user = CustomUser.objects.create_user(
            username='docentearchivable',
            email='docentearchivable@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Archivable', email=teacher_user.email)
        level = Level.objects.create(number=7, name='Nivel archivo', order=7)
        subject = Subject.objects.create(name='Materia Archivo')
        plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Plan preservado', topic='Archivo', objective='Conservar evidencia.')
        self.client.force_login(admin)

        response = self.client.post(reverse('dashboard:admin_resource_delete', args=['profesores', teacher.pk]))
        teacher.refresh_from_db()
        teacher_user.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['profesores']))
        self.assertFalse(teacher.is_active)
        self.assertFalse(teacher_user.is_active)
        self.assertTrue(LessonPlan.objects.filter(pk=plan.pk, teacher=teacher).exists())

    def test_inactive_teacher_cannot_login_with_teacher_profile_password(self):
        teacher = TeacherProfile.objects.create(
            name='Docente Inactivo Login',
            email='docenteinactivo@example.com',
            is_active=False,
        )
        teacher.set_password('Docente123!')
        teacher.save()

        response = self.client.post(reverse('accounts:login'), {
            'username': teacher.email,
            'password': 'Docente123!',
        })

        self.assertEqual(response.status_code, 200)
        self.assertFalse('_auth_user_id' in self.client.session)

    def test_admin_deactivates_teacher_profile_without_user(self):
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
        teacher.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['profesores']))
        self.assertFalse(teacher.is_active)

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
