from django.test import TestCase
from django.urls import reverse
from unittest.mock import patch

from accounts.models import CustomUser
from dashboard.forms import QuickStudentCreationForm
from activities.models import Activity
from games.models import Game, GameAttempt, GameAttemptAnswer
from learning.models import LessonPlan, LessonPlanAssignment, Level, ParentProfile, StudentProfile, Subject, TeacherProfile


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
        self.assertEqual(len(password), 4)
        self.assertTrue(password.isdigit())
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

    def test_student_report_shows_quiz_progress_by_subject(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Matemática')
        user = CustomUser.objects.create_user(
            username='alumnoquizreporte',
            email='alumnoquizreporte@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        student = StudentProfile.objects.create(user=user, name='Alumno Quiz Reporte', grade='1', reading_level=level, current_level=level)
        game = Game.objects.create(level=level, subject=subject, grade='1', name='Quiz', slug='quiz-reporte', description='Quiz', skill='Agilidad', game_type=Game.GameType.DYSLEXIA_QUIZ)
        attempt = GameAttempt.objects.create(student=student, game=game, score=50, correct_answers=1, total_questions=2)
        GameAttemptAnswer.objects.create(attempt=attempt, subject='Matemática', question='¿Cuánto es 1 + 1?', correct_answer='2', selected_answer='2', is_correct=True)
        GameAttemptAnswer.objects.create(attempt=attempt, subject='Matemática', question='¿Cuánto es 2 + 1?', correct_answer='3', selected_answer='4', is_correct=False)
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertContains(response, 'Progreso del quiz por materia')
        self.assertContains(response, 'Matemática')
        self.assertContains(response, '1/2')
        self.assertContains(response, '50%')


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

    def test_teacher_resource_cards_link_to_teacher_pages(self):
        self.teacher.can_create_students = True
        self.teacher.can_manage_activities = True
        self.teacher.can_manage_lessons = True
        self.teacher.can_manage_readings = True
        self.teacher.save(update_fields=['can_create_students', 'can_manage_activities', 'can_manage_lessons', 'can_manage_readings'])

        response = self.client.get(reverse('dashboard:teacher'))

        self.assertContains(response, reverse('dashboard:teacher_students'))
        self.assertContains(response, reverse('dashboard:teacher_resource', args=['actividades']))
        self.assertContains(response, reverse('dashboard:teacher_resource', args=['clases']))
        self.assertContains(response, reverse('dashboard:teacher_resource', args=['lecturas']))
        self.assertNotContains(response, reverse('dashboard:admin_resource', args=['actividades']))

    def test_teacher_resource_page_uses_teacher_layout(self):
        self.teacher.can_manage_activities = True
        self.teacher.save(update_fields=['can_manage_activities'])

        response = self.client.get(reverse('dashboard:teacher_resource', args=['actividades']))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestiona actividades según tus permisos docentes.')
        self.assertNotContains(response, 'Panel de control')

    def test_teacher_resource_actions_return_to_teacher_resource_page(self):
        self.teacher.can_manage_activities = True
        self.teacher.save(update_fields=['can_manage_activities'])
        activity = Activity.objects.create(
            level=self.level,
            subject=self.subject,
            grade='1',
            title='Actividad docente',
            activity_type=Activity.ActivityType.READING,
        )

        response = self.client.post(reverse('dashboard:teacher_resource_delete', args=['actividades', activity.pk]))

        self.assertRedirects(response, reverse('dashboard:teacher_resource', args=['actividades']))

    def test_teacher_students_page_lists_students_and_add_button(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(
            username='alumnopagina',
            email='alumnopagina@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        student = StudentProfile.objects.create(user=student_user, name='Alumno Página', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.get(reverse('dashboard:teacher_students'))

        self.assertContains(response, 'Mis alumnos')
        self.assertContains(response, 'Alumno Página')
        self.assertContains(response, reverse('dashboard:quick_student_create'))
        self.assertContains(response, reverse('dashboard:teacher_student_update', args=[student.pk]))
        self.assertContains(response, reverse('dashboard:teacher_student_delete', args=[student.pk]))

    def test_teacher_can_update_linked_student(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoeditar', email='alumnoeditar@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Editar', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': 'Alumno Editado',
            'alias': 'Editado',
            'grade': '2',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'current_level': self.level.pk,
        })
        student.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        self.assertEqual(student.name, 'Alumno Editado')
        self.assertEqual(student.alias, 'Editado')

    def test_teacher_can_start_linked_student_session(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoentrar', email='alumnoentrar@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Entrar', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[student.pk]))

        self.assertRedirects(response, reverse('dashboard:student'))
        self.assertEqual(int(self.client.session['_auth_user_id']), student_user.pk)

    def test_teacher_cannot_start_unlinked_student_session(self):
        student_user = CustomUser.objects.create_user(username='alumnoentrarajeno', email='alumnoentrarajeno@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Entrar Ajeno', grade='1', reading_level=self.level, current_level=self.level)

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[student.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_teacher_cannot_update_unlinked_student(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoajenoupdate', email='alumnoajenoupdate@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Ajeno Update', grade='1', reading_level=self.level, current_level=self.level)

        response = self.client.get(reverse('dashboard:teacher_student_update', args=[student.pk]))

        self.assertEqual(response.status_code, 404)

    def test_teacher_cannot_link_parent_to_unlinked_student(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        parent_user = CustomUser.objects.create_user(username='tutorajeno', email='tutorajeno@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        parent = ParentProfile.objects.create(user=parent_user, name='Tutor Ajeno')
        student_user = CustomUser.objects.create_user(username='alumnoajenotutor', email='alumnoajenotutor@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Ajeno Tutor', grade='1', reading_level=self.level, current_level=self.level)

        response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': student.name,
            'alias': '',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'current_level': self.level.pk,
            'parents': [parent.pk],
        })

        self.assertEqual(response.status_code, 404)
        self.assertFalse(parent.students.filter(pk=student.pk).exists())

    def test_teacher_delete_unlinked_student_returns_404(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoajenodelete', email='alumnoajenodelete@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Ajeno Delete', grade='1', reading_level=self.level, current_level=self.level)

        response = self.client.post(reverse('dashboard:teacher_student_delete', args=[student.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertTrue(StudentProfile.objects.filter(pk=student.pk).exists())

    def test_teacher_delete_student_with_history_deactivates_and_unlinks(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnohistorial', email='alumnohistorial@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Historial', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan historial', topic='Historial', objective='Conservar historial.')
        LessonPlanAssignment.objects.create(plan=plan, student=student)

        response = self.client.post(reverse('dashboard:teacher_student_delete', args=[student.pk]))
        student_user.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        self.assertFalse(student_user.is_active)
        self.assertFalse(self.teacher.students.filter(pk=student.pk).exists())

    def test_linked_teacher_can_regenerate_student_visual_key(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnodibujos', email='alumnodibujos@example.com', password='2468', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Dibujos', grade='1', reading_level=self.level, current_level=self.level)
        student.set_visual_key(['dog', 'star', 'car'])
        student.save(update_fields=['visual_key_hash'])
        old_hash = student.visual_key_hash
        self.teacher.students.add(student)

        with patch('learning.models.secrets.SystemRandom.sample', return_value=['book', 'sun', 'fish']):
            response = self.client.post(reverse('dashboard:teacher_student_visual_key_regenerate', args=[student.pk]), {'had_visual_key': '1'})
        student.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tarjeta de acceso')
        self.assertNotEqual(student.visual_key_hash, old_hash)
        self.assertFalse(student.check_visual_key(['dog', 'star', 'car']))
        self.assertTrue(student.check_visual_key(['book', 'sun', 'fish']))

    def test_unlinked_teacher_cannot_regenerate_student_visual_key(self):
        other_teacher_user = CustomUser.objects.create_user(username='docenteajeno', email='docenteajeno@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        TeacherProfile.objects.create(user=other_teacher_user, name='Docente Ajeno', can_create_students=True)
        student_user = CustomUser.objects.create_user(username='alumnodibujosajeno', email='alumnodibujosajeno@example.com', password='2468', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Dibujos Ajeno', grade='1', reading_level=self.level, current_level=self.level)
        student.set_visual_key(['dog', 'star', 'car'])
        student.save(update_fields=['visual_key_hash'])
        old_hash = student.visual_key_hash

        response = self.client.post(reverse('dashboard:teacher_student_visual_key_regenerate', args=[student.pk]), {'had_visual_key': '1'})
        student.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)
        self.assertEqual(student.visual_key_hash, old_hash)

    def test_old_student_without_visual_key_can_receive_one(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoantiguo', email='alumnoantiguo@example.com', password='2468', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Antiguo', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)
        self.assertEqual(student.visual_key_hash, '')

        with patch('learning.models.secrets.SystemRandom.sample', return_value=['apple', 'house', 'car']):
            response = self.client.post(reverse('dashboard:teacher_student_visual_key_regenerate', args=[student.pk]), {'had_visual_key': '0'})
        student.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Guarda esta tarjeta en un lugar seguro')
        self.assertTrue(student.check_visual_key(['apple', 'house', 'car']))


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


class AcademicRelationshipPermissionTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.teacher_user = CustomUser.objects.create_user(
            username='docentevinculado',
            email='docentevinculado@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(
            user=self.teacher_user,
            name='Docente Vinculado',
            can_create_students=True,
            can_create_lesson_plans=True,
            can_view_student_reports=True,
        )
        self.linked_user = CustomUser.objects.create_user(
            username='alumnovinculado',
            email='alumnovinculado@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.linked_student = StudentProfile.objects.create(
            user=self.linked_user,
            name='Alumno Vinculado',
            grade='1',
            reading_level=self.level,
            current_level=self.level,
        )
        self.other_user = CustomUser.objects.create_user(
            username='alumnoajeno',
            email='alumnoajeno@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.other_student = StudentProfile.objects.create(
            user=self.other_user,
            name='Alumno Ajeno',
            grade='1',
            reading_level=self.level,
            current_level=self.level,
        )
        self.teacher.students.add(self.linked_student)

    def test_teacher_dashboard_shows_only_linked_students(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse('dashboard:teacher'))

        self.assertContains(response, 'Alumno Vinculado')
        self.assertNotContains(response, 'Alumno Ajeno')

    def test_teacher_cannot_view_unlinked_student_report_by_pk(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse('dashboard:student_report', args=[self.other_student.pk]))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)

    def test_teacher_can_view_linked_student_report(self):
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse('dashboard:student_report', args=[self.linked_student.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alumno Vinculado')

    def test_quick_student_creation_links_student_to_teacher(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:quick_student_create'), data={
            'name': 'Nuevo Alumno',
            'alias': 'Nuevo',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
        })

        self.assertEqual(response.status_code, 200)
        student = StudentProfile.objects.get(name='Nuevo Alumno')
        self.assertTrue(self.teacher.students.filter(pk=student.pk).exists())

    def test_quick_student_creation_links_existing_parent(self):
        parent_user = CustomUser.objects.create_user(username='tutorexistente', email='tutorexistente@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        parent = ParentProfile.objects.create(user=parent_user, name='Tutor Existente')
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:quick_student_create'), data={
            'name': 'Alumno Con Tutor',
            'alias': 'Tutor',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'parents': [parent.pk],
        })

        self.assertEqual(response.status_code, 200)
        student = StudentProfile.objects.get(name='Alumno Con Tutor')
        self.assertTrue(parent.students.filter(pk=student.pk).exists())

    def test_quick_student_creation_creates_and_links_new_parent(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:quick_student_create'), data={
            'name': 'Alumno Tutor Nuevo',
            'alias': 'Nuevo',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'new_parent_first_name': 'Maria',
            'new_parent_last_name': 'Tutor',
            'new_parent_email': 'maria.tutor@example.com',
        })

        self.assertEqual(response.status_code, 200)
        student = StudentProfile.objects.get(name='Alumno Tutor Nuevo')
        parent = ParentProfile.objects.get(user__email='maria.tutor@example.com')
        self.assertTrue(parent.students.filter(pk=student.pk).exists())

    def test_teacher_cannot_assign_unlinked_student_to_lesson_plan(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_create'), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': 'Plan seguro',
            'topic': 'Seguridad',
            'objective': 'Validar estudiantes vinculados.',
            'assigned_students': [self.linked_student.pk, self.other_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escoja una opción válida')
        self.assertFalse(LessonPlan.objects.filter(title='Plan seguro').exists())

    def test_parent_dashboard_shows_only_linked_students(self):
        parent_user = CustomUser.objects.create_user(
            username='padrevinculado',
            email='padrevinculado@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        parent = ParentProfile.objects.create(user=parent_user, name='Padre Vinculado')
        parent.students.add(self.linked_student)
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:parents'))

        self.assertContains(response, 'Alumno Vinculado')
        self.assertNotContains(response, 'Alumno Ajeno')

    def test_parent_can_view_only_linked_student_report(self):
        parent_user = CustomUser.objects.create_user(
            username='padreinforme',
            email='padreinforme@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        parent = ParentProfile.objects.create(user=parent_user, name='Padre Informe')
        parent.students.add(self.linked_student)
        self.client.force_login(parent_user)

        linked_response = self.client.get(reverse('dashboard:student_report', args=[self.linked_student.pk]))
        unlinked_response = self.client.get(reverse('dashboard:student_report', args=[self.other_student.pk]))

        self.assertEqual(linked_response.status_code, 200)
        self.assertRedirects(unlinked_response, reverse('dashboard:redirect'), fetch_redirect_response=False)

    def test_plain_staff_user_cannot_view_student_report_without_admin_role(self):
        staff_user = CustomUser.objects.create_user(
            username='staffsinrol',
            email='staffsinrol@example.com',
            password='Staff12345!',
            role=CustomUser.Role.TEACHER,
            is_staff=True,
        )
        self.client.force_login(staff_user)

        response = self.client.get(reverse('dashboard:student_report', args=[self.linked_student.pk]))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)

    def test_admin_role_keeps_global_student_report_access(self):
        admin = CustomUser.objects.create_user(
            username='adminreportes',
            email='adminreportes@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        self.client.force_login(admin)

        response = self.client.get(reverse('dashboard:student_report', args=[self.other_student.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alumno Ajeno')
