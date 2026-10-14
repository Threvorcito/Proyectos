import json

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from unittest.mock import patch

from accounts.models import CustomUser
from dashboard.forms import LessonPlanForm, QuickStudentCreationForm
from dashboard.views import TEACHER_IMPERSONATION_PROFILE_KEY, TEACHER_IMPERSONATION_STUDENT_KEY, TEACHER_IMPERSONATION_USER_KEY, resource_has_history
from activities.models import Activity, ActivityOption
from gamification.models import Achievement, StudentAchievement
from games.models import Game, GameAttempt, GameAttemptAnswer
from learning.models import CurriculumCompetency, LessonPlan, LessonPlanAssignment, Level, ParentProfile, StudentProfile, Subject, TeacherProfile
from progress.models import ActivityAttempt, StudentDifficulty, StudentProgress
from readings.models import Reading, ReadingAnswer, ReadingComprehensionAnswer, ReadingProgress, ReadingQuestion


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


class FooterRoleVisibilityTests(TestCase):
    def test_parent_footer_hides_student_resource_links(self):
        parent_user = CustomUser.objects.create_user(
            username='tutorfooter',
            email='tutorfooter@example.com',
            password='Demo12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Tutor Footer')
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:parents'))

        self.assertContains(response, 'Panel familiar')
        self.assertNotContains(response, 'Aprender</a>')
        self.assertNotContains(response, 'Actividades</a>')
        self.assertNotContains(response, 'Lecturas</a>')

    def test_student_footer_shows_student_resource_links(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        student_user = CustomUser.objects.create_user(
            username='alumnofooter',
            email='alumnofooter@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student_user, name='Alumno Footer', grade='1', reading_level=level, current_level=level)
        self.client.force_login(student_user)

        response = self.client.get(reverse('dashboard:student'))

        self.assertContains(response, 'Aprender')
        self.assertContains(response, 'Actividades')
        self.assertContains(response, 'Lecturas')


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


class TeacherStudentImpersonationTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.teacher_user = CustomUser.objects.create_user(
            username='docentevista',
            email='docentevista@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, name='Docente Vista')
        self.student_user = CustomUser.objects.create_user(
            username='alumnovista',
            email='alumnovista@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.student_user,
            name='Maria Vista',
            grade='1',
            reading_level=self.level,
            current_level=self.level,
        )
        self.other_user = CustomUser.objects.create_user(
            username='alumnoajenoimp',
            email='alumnoajenoimp@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.other_student = StudentProfile.objects.create(
            user=self.other_user,
            name='Alumno Ajeno Imp',
            grade='1',
            reading_level=self.level,
            current_level=self.level,
        )
        self.teacher.students.add(self.student)

    def test_linked_teacher_can_view_as_student(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[self.student.pk]))

        self.assertRedirects(response, reverse('dashboard:student'))
        session = self.client.session
        self.assertEqual(int(session['_auth_user_id']), self.student_user.pk)
        self.assertEqual(session[TEACHER_IMPERSONATION_USER_KEY], self.teacher_user.pk)
        self.assertEqual(session[TEACHER_IMPERSONATION_PROFILE_KEY], self.teacher.pk)
        self.assertEqual(session[TEACHER_IMPERSONATION_STUDENT_KEY], self.student.pk)

    def test_unlinked_teacher_cannot_view_as_student(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[self.other_student.pk]))

        self.assertEqual(response.status_code, 404)
        session = self.client.session
        self.assertEqual(int(session['_auth_user_id']), self.teacher_user.pk)
        self.assertNotIn(TEACHER_IMPERSONATION_USER_KEY, session)

    def test_return_to_teacher_restores_original_account_and_cleans_session(self):
        self.client.force_login(self.teacher_user)
        self.client.post(reverse('dashboard:teacher_student_login', args=[self.student.pk]))

        response = self.client.post(reverse('dashboard:teacher_student_return'))

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        session = self.client.session
        self.assertEqual(int(session['_auth_user_id']), self.teacher_user.pk)
        self.assertNotIn(TEACHER_IMPERSONATION_USER_KEY, session)
        self.assertNotIn(TEACHER_IMPERSONATION_PROFILE_KEY, session)
        self.assertNotIn(TEACHER_IMPERSONATION_STUDENT_KEY, session)

    def test_impersonation_banner_appears_for_view_as_student(self):
        self.client.force_login(self.teacher_user)
        self.client.post(reverse('dashboard:teacher_student_login', args=[self.student.pk]))

        response = self.client.get(reverse('dashboard:student'))

        self.assertContains(response, 'Estás viendo la cuenta de Maria Vista como docente.')
        self.assertContains(response, 'Volver a mi cuenta docente')

    def test_nested_impersonation_is_not_allowed(self):
        self.client.force_login(self.teacher_user)
        session = self.client.session
        session[TEACHER_IMPERSONATION_USER_KEY] = self.teacher_user.pk
        session.save()

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[self.student.pk]))

        self.assertRedirects(response, reverse('dashboard:student'), fetch_redirect_response=False)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.teacher_user.pk)

    def test_regular_student_cannot_start_teacher_impersonation(self):
        self.client.force_login(self.student_user)

        response = self.client.post(reverse('dashboard:teacher_student_login', args=[self.other_student.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.student_user.pk)
        self.assertNotIn(TEACHER_IMPERSONATION_USER_KEY, self.client.session)

    def test_invalid_return_session_logs_out_safely(self):
        self.client.force_login(self.student_user)
        session = self.client.session
        session[TEACHER_IMPERSONATION_USER_KEY] = 99999
        session[TEACHER_IMPERSONATION_PROFILE_KEY] = 99999
        session[TEACHER_IMPERSONATION_STUDENT_KEY] = self.student.pk
        session.save()

        response = self.client.post(reverse('dashboard:teacher_student_return'))

        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)


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

    def test_student_dashboard_hides_draft_and_inactive_assigned_plans(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        teacher_user = CustomUser.objects.create_user(username='docentevisibilidad', email='docentevisibilidad@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Visibilidad')
        student_user = CustomUser.objects.create_user(username='alumnovisibilidad', email='alumnovisibilidad@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Visibilidad', grade='1', reading_level=level, current_level=level)
        active_plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Clase activa visible', topic='Lectura', objective='Leer.', status=LessonPlan.Status.ACTIVE, is_active=True)
        draft_plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Clase borrador oculta', topic='Lectura', objective='Leer.', status=LessonPlan.Status.DRAFT, is_active=True)
        inactive_plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Clase inactiva oculta', topic='Lectura', objective='Leer.', status=LessonPlan.Status.ACTIVE, is_active=False)
        LessonPlanAssignment.objects.create(plan=active_plan, student=student)
        LessonPlanAssignment.objects.create(plan=draft_plan, student=student)
        LessonPlanAssignment.objects.create(plan=inactive_plan, student=student)
        self.client.force_login(student_user)

        response = self.client.get(reverse('dashboard:student'))

        self.assertContains(response, 'Continuar mi clase')
        self.assertContains(response, 'Clase activa visible')
        self.assertNotContains(response, 'Clase borrador oculta')
        self.assertNotContains(response, 'Clase inactiva oculta')

    def test_student_cannot_open_draft_or_inactive_assigned_plan(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        teacher_user = CustomUser.objects.create_user(username='docentenoabre', email='docentenoabre@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente No Abre')
        student_user = CustomUser.objects.create_user(username='alumnonoabre', email='alumnonoabre@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno No Abre', grade='1', reading_level=level, current_level=level)
        draft_plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Borrador directo', topic='Lectura', objective='Leer.', status=LessonPlan.Status.DRAFT)
        inactive_plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Inactivo directo', topic='Lectura', objective='Leer.', is_active=False)
        LessonPlanAssignment.objects.create(plan=draft_plan, student=student)
        LessonPlanAssignment.objects.create(plan=inactive_plan, student=student)
        self.client.force_login(student_user)

        draft_response = self.client.get(reverse('dashboard:student_lesson_plan', args=[draft_plan.pk]))
        inactive_response = self.client.get(reverse('dashboard:student_lesson_plan', args=[inactive_plan.pk]))

        self.assertEqual(draft_response.status_code, 404)
        self.assertEqual(inactive_response.status_code, 404)

    def test_student_lesson_plan_shows_only_linked_resources(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        teacher_user = CustomUser.objects.create_user(username='docenterecursosplan', email='docenterecursosplan@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Recursos Plan')
        student_user = CustomUser.objects.create_user(username='alumnorecursosplan', email='alumnorecursosplan@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Recursos Plan', grade='1', reading_level=level, current_level=level)
        activity = Activity.objects.create(level=level, subject=subject, grade='1', title='Actividad asignada al plan', activity_type=Activity.ActivityType.READING)
        reading = Reading.objects.create(level=level, subject=subject, grade='1', title='Lectura asignada al plan', content='Texto')
        linked_game = Game.objects.create(level=level, subject=subject, grade='1', name='Juego asignado al plan', slug='juego-asignado-al-plan', description='Juego', skill='Memoria', game_type=Game.GameType.MEMORY)
        Game.objects.create(level=level, subject=subject, grade='1', name='Juego no vinculado', slug='juego-no-vinculado-plan', description='Juego', skill='Memoria', game_type=Game.GameType.MEMORY)
        plan = LessonPlan.objects.create(teacher=teacher, subject=subject, level=level, grade='1', title='Clase con recursos vinculados', topic='Lectura', objective='Leer.', status=LessonPlan.Status.ACTIVE, is_active=True)
        plan.activities.add(activity)
        plan.readings.add(reading)
        plan.games.add(linked_game)
        LessonPlanAssignment.objects.create(plan=plan, student=student)
        self.client.force_login(student_user)

        response = self.client.get(reverse('dashboard:student_lesson_plan', args=[plan.pk]))

        self.assertContains(response, 'Actividad asignada al plan')
        self.assertContains(response, 'Lectura asignada al plan')
        self.assertContains(response, 'Juego asignado al plan')
        self.assertNotContains(response, 'Juego no vinculado')

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

    def test_student_report_shows_reading_progress_and_rewards(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        user = CustomUser.objects.create_user(username='alumnolecturareporte', email='alumnolecturareporte@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=user, name='Alumno Lectura Reporte', grade='1', reading_level=level, current_level=level, points=20, stars=2)
        reading = Reading.objects.create(level=level, subject=subject, grade='1', title='La casa azul', content='La casa es azul.')
        question_one = ReadingQuestion.objects.create(reading=reading, question='¿De qué color es la casa?')
        question_two = ReadingQuestion.objects.create(reading=reading, question='¿Qué es azul?')
        ReadingAnswer.objects.create(question=question_one, answer='Azul', is_correct=True)
        ReadingAnswer.objects.create(question=question_two, answer='La casa', is_correct=True)
        ReadingComprehensionAnswer.objects.create(student=student, reading=reading, question=question_one, selected_answer='Azul', is_correct=True)
        ReadingComprehensionAnswer.objects.create(student=student, reading=reading, question=question_two, selected_answer='El perro', is_correct=False)
        ReadingProgress.objects.create(student=student, reading=reading, completed=True, comprehension_percentage=50)
        achievement = Achievement.objects.create(name='Primer lector', description='Completa una lectura.', icon='📚', requirement_type='readings', requirement_value=1)
        StudentAchievement.objects.create(student=student, achievement=achievement)
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertContains(response, 'Lecturas y comprensión')
        self.assertContains(response, 'La casa azul')
        self.assertContains(response, 'Completada')
        self.assertContains(response, '50%')
        self.assertContains(response, '1/2 correctas')
        self.assertContains(response, '20 puntos')
        self.assertContains(response, '2 estrellas')
        self.assertContains(response, 'Primer lector')

    def test_linked_teacher_can_view_student_report_with_reading_data(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        teacher_user = CustomUser.objects.create_user(username='docenteautorizado', email='docenteautorizado@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Autorizado', can_view_student_reports=True)
        student_user = CustomUser.objects.create_user(username='alumnodocenteautorizado', email='alumnodocenteautorizado@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Docente Autorizado', grade='1', reading_level=level, current_level=level)
        teacher.students.add(student)
        reading = Reading.objects.create(level=level, grade='1', title='Lectura visible docente', content='Texto.')
        ReadingProgress.objects.create(student=student, reading=reading, completed=True, comprehension_percentage=100)
        self.client.force_login(teacher_user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertContains(response, 'Lectura visible docente')
        self.assertContains(response, 'Lecturas y comprensión')

    def test_unlinked_teacher_cannot_view_student_report(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        teacher_user = CustomUser.objects.create_user(username='docenteajeno', email='docenteajeno@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        TeacherProfile.objects.create(user=teacher_user, name='Docente Ajeno', can_view_student_reports=True)
        student_user = CustomUser.objects.create_user(username='alumnoajeno', email='alumnoajeno@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Ajeno', grade='1', reading_level=level, current_level=level)
        self.client.force_login(teacher_user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)

    def test_linked_parent_can_view_student_report_with_reading_data(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        parent_user = CustomUser.objects.create_user(username='tutorautorizado', email='tutorautorizado@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        parent = ParentProfile.objects.create(user=parent_user, name='Tutor Autorizado')
        student_user = CustomUser.objects.create_user(username='alumnotutorautorizado', email='alumnotutorautorizado@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Tutor Autorizado', grade='1', reading_level=level, current_level=level)
        parent.students.add(student)
        reading = Reading.objects.create(level=level, grade='1', title='Lectura visible tutor', content='Texto.')
        ReadingProgress.objects.create(student=student, reading=reading, completed=False, comprehension_percentage=0)
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertContains(response, 'Lectura visible tutor')
        self.assertContains(response, 'En progreso')

    def test_unlinked_parent_cannot_view_student_report(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        parent_user = CustomUser.objects.create_user(username='tutorajeno2', email='tutorajeno2@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        ParentProfile.objects.create(user=parent_user, name='Tutor Ajeno')
        student_user = CustomUser.objects.create_user(username='alumnotutorajeno', email='alumnotutorajeno@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Tutor Ajeno', grade='1', reading_level=level, current_level=level)
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:student_report', args=[student.pk]))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)


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
        self.assertNotContains(response, reverse('dashboard:teacher_resource', args=['clases']))
        self.assertContains(response, reverse('dashboard:teacher_resource', args=['lecturas']))
        self.assertNotContains(response, reverse('dashboard:admin_resource', args=['actividades']))

    def test_teacher_cannot_manage_lessons_resource_even_with_legacy_permission(self):
        self.teacher.can_manage_lessons = True
        self.teacher.save(update_fields=['can_manage_lessons'])

        response = self.client.get(reverse('dashboard:teacher_resource', args=['clases']))

        self.assertRedirects(response, reverse('dashboard:redirect'), fetch_redirect_response=False)

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
        self.assertContains(response, 'data-bs-target="#createStudentModal"')
        self.assertContains(response, 'Registrar estudiante')
        self.assertContains(response, 'Padre, madre o tutor')
        self.assertContains(response, reverse('dashboard:teacher_student_update', args=[student.pk]))
        self.assertContains(response, f'data-bs-target="#editStudentModal{student.pk}"')
        self.assertContains(response, 'Editar estudiante')
        self.assertContains(response, 'Datos del estudiante')
        self.assertContains(response, 'Información académica')
        self.assertContains(response, 'Apoyo al aprendizaje')
        self.assertNotContains(response, 'Tutores vinculados')
        self.assertContains(response, reverse('dashboard:teacher_student_delete', args=[student.pk]))

    def test_teacher_creates_student_from_students_page_modal(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])

        response = self.client.post(reverse('dashboard:teacher_students'), data={
            'name': 'Alumno Modal',
            'alias': 'Modal',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
        })

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        student = StudentProfile.objects.get(name='Alumno Modal')
        self.assertTrue(self.teacher.students.filter(pk=student.pk).exists())

    def test_teacher_students_create_modal_reopens_with_errors(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])

        response = self.client.post(reverse('dashboard:teacher_students'), data={
            'name': '',
            'alias': 'Error',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="createStudentModal"')
        self.assertContains(response, 'show')
        self.assertContains(response, 'Este campo es obligatorio')

    def test_teacher_students_create_modal_shows_parent_names(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        parent_user = CustomUser.objects.create_user(username='tutormodal', email='tutormodal@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        ParentProfile.objects.create(user=parent_user, name='María López')

        response = self.client.get(reverse('dashboard:teacher_students'))

        self.assertContains(response, 'María López')
        self.assertNotContains(response, 'ParentProfile object')

    def test_teacher_can_update_linked_student(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoeditar', email='alumnoeditar@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Editar', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': 'Alumno Editado',
            'alias': 'Editado',
            'birth_date': '2018-05-10',
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
        self.assertEqual(student.grade, '2')
        self.assertEqual(student.school, 'public')
        self.assertEqual(student.modality, 'regular')
        self.assertEqual(student.zone, 'urban')

    def test_teacher_can_see_and_change_student_tutor_in_modal(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnotutor', email='alumnotutor@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Tutor', grade='1', reading_level=self.level, current_level=self.level)
        other_user = CustomUser.objects.create_user(username='alumnotutorotro', email='alumnotutorotro@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        other_student = StudentProfile.objects.create(user=other_user, name='Alumno Otro Tutor', grade='1', reading_level=self.level, current_level=self.level)
        current_parent_user = CustomUser.objects.create_user(username='tutoractual', email='tutoractual@example.com', password='Padre12345!', role=CustomUser.Role.PARENT)
        new_parent_user = CustomUser.objects.create_user(username='tutornuevo', email='tutornuevo@example.com', password='Padre12345!', role=CustomUser.Role.PARENT)
        current_parent = ParentProfile.objects.create(user=current_parent_user, name='María López')
        new_parent = ParentProfile.objects.create(user=new_parent_user, name='Carlos Ruiz')
        current_parent.students.add(student, other_student)
        self.teacher.students.add(student)

        response = self.client.get(reverse('dashboard:teacher_students'))

        self.assertContains(response, 'Tutor del estudiante')
        self.assertContains(response, 'María López')
        self.assertContains(response, 'Cambiar tutor')
        self.assertContains(response, 'Carlos Ruiz')

        post_response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': 'Alumno Tutor',
            'alias': '',
            'birth_date': '',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'current_level': self.level.pk,
            'parents': [new_parent.pk],
        })
        student.refresh_from_db()
        other_student.refresh_from_db()

        self.assertRedirects(post_response, reverse('dashboard:teacher_students'))
        self.assertQuerySetEqual(student.parents.order_by('name'), [new_parent], transform=lambda parent: parent)
        self.assertQuerySetEqual(other_student.parents.order_by('name'), [current_parent], transform=lambda parent: parent)

    def test_teacher_can_remove_tutor_link_without_deleting_parent_account(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoquitartutor', email='alumnoquitartutor@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Quitar Tutor', grade='1', reading_level=self.level, current_level=self.level)
        other_user = CustomUser.objects.create_user(username='alumnootrotutor', email='alumnootrotutor@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        other_student = StudentProfile.objects.create(user=other_user, name='Alumno Otro Tutor', grade='1', reading_level=self.level, current_level=self.level)
        parent_user = CustomUser.objects.create_user(username='tutorconvarios', email='tutorconvarios@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        parent = ParentProfile.objects.create(user=parent_user, name='Tutor Con Varios')
        parent.students.add(student, other_student)
        self.teacher.students.add(student)

        response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': student.name,
            'alias': '',
            'birth_date': '',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'current_level': self.level.pk,
        })

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        self.assertTrue(ParentProfile.objects.filter(pk=parent.pk).exists())
        self.assertTrue(CustomUser.objects.filter(pk=parent_user.pk, is_active=True).exists())
        self.assertFalse(parent.students.filter(pk=student.pk).exists())
        self.assertTrue(parent.students.filter(pk=other_student.pk).exists())

    def test_teacher_student_update_errors_render_inside_students_page(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnoerror', email='alumnoerror@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Error', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.post(reverse('dashboard:teacher_student_update', args=[student.pk]), data={
            'name': '',
            'alias': 'Error',
            'birth_date': '',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'current_level': self.level.pk,
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mis alumnos')
        self.assertContains(response, 'Editar estudiante')
        self.assertContains(response, 'Este campo es obligatorio')

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

    def test_teacher_unlinks_student_without_deactivating_or_deleting_history(self):
        self.teacher.can_create_students = True
        self.teacher.can_view_student_reports = True
        self.teacher.save(update_fields=['can_create_students', 'can_view_student_reports'])
        second_teacher_user = CustomUser.objects.create_user(username='docentesegundo', email='docentesegundo@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        second_teacher = TeacherProfile.objects.create(user=second_teacher_user, name='Docente Segundo')
        parent_user = CustomUser.objects.create_user(username='tutorhistorial', email='tutorhistorial@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        parent = ParentProfile.objects.create(user=parent_user, name='Tutor Historial')
        student_user = CustomUser.objects.create_user(username='alumnohistorial', email='alumnohistorial@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Historial', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)
        second_teacher.students.add(student)
        parent.students.add(student)
        activity = Activity.objects.create(level=self.level, subject=self.subject, grade='1', title='Actividad historial', activity_type=Activity.ActivityType.READING)
        ActivityAttempt.objects.create(student=student, activity=activity, answer='a', is_correct=True)
        StudentProgress.objects.create(student=student, activity=activity, completed=True, progress_percentage=100, best_score=100, attempts=1)
        StudentDifficulty.objects.create(student=student, difficulty_type='letter_confusion', character_a='b', character_b='d', error_count=1)
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura historial', content='Texto.')
        question = ReadingQuestion.objects.create(reading=reading, question='Pregunta')
        ReadingProgress.objects.create(student=student, reading=reading, completed=True, comprehension_percentage=100)
        ReadingComprehensionAnswer.objects.create(student=student, reading=reading, question=question, selected_answer='Respuesta', is_correct=True)
        game = Game.objects.create(level=self.level, subject=self.subject, grade='1', name='Juego historial', slug='juego-historial-alumno', description='Juego', skill='Lectura', game_type=Game.GameType.MEMORY)
        GameAttempt.objects.create(student=student, game=game, score=100, correct_answers=1, total_questions=1, completed=True)
        achievement = Achievement.objects.create(name='Logro historial', description='Logro', requirement_type='activity', requirement_value=1)
        StudentAchievement.objects.create(student=student, achievement=achievement)

        response = self.client.post(reverse('dashboard:teacher_student_delete', args=[student.pk]))
        student_user.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:teacher_students'))
        self.assertTrue(StudentProfile.objects.filter(pk=student.pk).exists())
        self.assertTrue(CustomUser.objects.filter(pk=student_user.pk).exists())
        self.assertTrue(student_user.is_active)
        self.assertFalse(self.teacher.students.filter(pk=student.pk).exists())
        self.assertTrue(second_teacher.students.filter(pk=student.pk).exists())
        self.assertTrue(parent.students.filter(pk=student.pk).exists())
        self.assertTrue(ActivityAttempt.objects.filter(student=student).exists())
        self.assertTrue(StudentProgress.objects.filter(student=student).exists())
        self.assertTrue(StudentDifficulty.objects.filter(student=student).exists())
        self.assertTrue(ReadingProgress.objects.filter(student=student).exists())
        self.assertTrue(ReadingComprehensionAnswer.objects.filter(student=student).exists())
        self.assertTrue(GameAttempt.objects.filter(student=student).exists())
        self.assertTrue(StudentAchievement.objects.filter(student=student).exists())

    def test_student_and_parent_cannot_unlink_teacher_student_relationship(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnonodesvincula', email='alumnonodesvincula@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno No Desvincula', grade='1', reading_level=self.level, current_level=self.level)
        parent_user = CustomUser.objects.create_user(username='tutornodesvincula', email='tutornodesvincula@example.com', password='Tutor12345!', role=CustomUser.Role.PARENT)
        ParentProfile.objects.create(user=parent_user, name='Tutor No Desvincula')
        self.teacher.students.add(student)

        self.client.force_login(parent_user)
        response = self.client.post(reverse('dashboard:teacher_student_delete', args=[student.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.teacher.students.filter(pk=student.pk).exists())

        self.client.force_login(student_user)
        response = self.client.post(reverse('dashboard:teacher_student_delete', args=[student.pk]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.teacher.students.filter(pk=student.pk).exists())

    def test_teacher_students_page_uses_unlink_copy(self):
        self.teacher.can_create_students = True
        self.teacher.save(update_fields=['can_create_students'])
        student_user = CustomUser.objects.create_user(username='alumnocopia', email='alumnocopia@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=student_user, name='Alumno Copia', grade='1', reading_level=self.level, current_level=self.level)
        self.teacher.students.add(student)

        response = self.client.get(reverse('dashboard:teacher_students'))

        self.assertContains(response, 'Quitar de mis alumnos')
        self.assertContains(response, '¿Quieres quitar a este estudiante de Mis alumnos?')
        self.assertContains(response, 'Su cuenta, progreso y demás información se conservarán')

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


class ResourceHistoryDetectionTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.student_user = CustomUser.objects.create_user(username='alumnohistoriarec', email='alumnohistoriarec@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        self.student = StudentProfile.objects.create(user=self.student_user, name='Alumno Historia Recurso', grade='1', reading_level=self.level, current_level=self.level)

    def test_reading_with_reading_progress_has_history(self):
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura con avance', content='Texto.')
        ReadingProgress.objects.create(student=self.student, reading=reading)

        self.assertTrue(resource_has_history(reading))

    def test_reading_with_comprehension_answer_has_history(self):
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura con respuesta', content='Texto.')
        question = ReadingQuestion.objects.create(reading=reading, question='Pregunta')
        ReadingComprehensionAnswer.objects.create(student=self.student, reading=reading, question=question, selected_answer='Respuesta', is_correct=True)

        self.assertTrue(resource_has_history(reading))

    def test_game_with_attempt_has_history(self):
        game = Game.objects.create(level=self.level, subject=self.subject, grade='1', name='Juego con intento', slug='juego-con-intento', description='Juego', skill='Lectura', game_type=Game.GameType.MEMORY)
        GameAttempt.objects.create(student=self.student, game=game, score=80, correct_answers=4, total_questions=5, completed=True)

        self.assertTrue(resource_has_history(game))

    def test_activity_with_history_has_history(self):
        activity = Activity.objects.create(level=self.level, subject=self.subject, grade='1', title='Actividad con historial', activity_type=Activity.ActivityType.READING)
        ActivityAttempt.objects.create(student=self.student, activity=activity, answer='a', is_correct=True)

        self.assertTrue(resource_has_history(activity))

    def test_student_with_reading_progress_has_history(self):
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura estudiante avance', content='Texto.')
        ReadingProgress.objects.create(student=self.student, reading=reading)

        self.assertTrue(resource_has_history(self.student))

    def test_student_with_comprehension_answer_has_history(self):
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura estudiante respuesta', content='Texto.')
        question = ReadingQuestion.objects.create(reading=reading, question='Pregunta')
        ReadingComprehensionAnswer.objects.create(student=self.student, reading=reading, question=question, selected_answer='Respuesta', is_correct=True)

        self.assertTrue(resource_has_history(self.student))

    def test_student_with_game_attempt_has_history(self):
        game = Game.objects.create(level=self.level, subject=self.subject, grade='1', name='Juego estudiante intento', slug='juego-estudiante-intento', description='Juego', skill='Lectura', game_type=Game.GameType.MEMORY)
        GameAttempt.objects.create(student=self.student, game=game, score=80, correct_answers=4, total_questions=5, completed=True)

        self.assertTrue(resource_has_history(self.student))

    def test_student_with_achievement_has_history(self):
        achievement = Achievement.objects.create(name='Logro estudiante', description='Logro', requirement_type='activity', requirement_value=1)
        StudentAchievement.objects.create(student=self.student, achievement=achievement)

        self.assertTrue(resource_has_history(self.student))

    def test_student_with_activity_progress_has_history(self):
        activity = Activity.objects.create(level=self.level, subject=self.subject, grade='1', title='Actividad progreso estudiante', activity_type=Activity.ActivityType.READING)
        StudentProgress.objects.create(student=self.student, activity=activity, completed=True, progress_percentage=100, best_score=100, attempts=1)

        self.assertTrue(resource_has_history(self.student))

    def test_resource_with_history_is_deactivated_without_losing_related_records(self):
        admin = CustomUser.objects.create_user(username='adminrecursohistoria', email='adminrecursohistoria@example.com', password='Admin12345!', role=CustomUser.Role.ADMIN, is_staff=True)
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura usada', content='Texto.', is_active=True)
        progress = ReadingProgress.objects.create(student=self.student, reading=reading)
        self.client.force_login(admin)

        response = self.client.post(reverse('dashboard:admin_resource_delete', args=['lecturas', reading.pk]))
        reading.refresh_from_db()

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['lecturas']))
        self.assertFalse(reading.is_active)
        self.assertTrue(ReadingProgress.objects.filter(pk=progress.pk, reading=reading).exists())


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

    def test_teacher_creates_lesson_plan_with_closing_games_activities_and_readings(self):
        activity = Activity.objects.create(
            level=self.level,
            subject=self.subject,
            grade='1',
            title='Ordena las sílabas',
            activity_type=Activity.ActivityType.SYLLABLES,
        )
        reading = Reading.objects.create(
            level=self.level,
            subject=self.subject,
            grade='1',
            title='El sol sale',
            content='El sol sale temprano.',
        )
        game_one = Game.objects.create(
            level=self.level,
            subject=self.subject,
            grade='1',
            name='Memoria de palabras',
            slug='memoria-palabras-plan',
            description='Juego de memoria',
            skill='Memoria visual',
            game_type=Game.GameType.MEMORY,
        )
        game_two = Game.objects.create(
            level=self.level,
            subject=self.subject,
            grade='',
            name='Camino de lectura',
            slug='camino-lectura-plan',
            description='Juego lector',
            skill='Fluidez',
            game_type=Game.GameType.READING_PATH,
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_create'), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': 'Plan con cierre y juegos',
            'topic': 'Sílabas',
            'objective': 'Practicar lectura de palabras breves.',
            'initial_activities': 'Recordar sonidos conocidos.',
            'teacher_reading': 'Leer el texto en voz alta.',
            'comprehension_orthography_activities': 'Responder preguntas y separar sílabas.',
            'closing_activities': 'Compartir una palabra aprendida y valorar el avance.',
            'activities': [activity.pk],
            'readings': [reading.pk],
            'games': [game_one.pk, game_two.pk],
            'assigned_students': [self.linked_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('dashboard:lesson_plans'))
        plan = LessonPlan.objects.get(title='Plan con cierre y juegos')
        self.assertEqual(plan.closing_activities, 'Compartir una palabra aprendida y valorar el avance.')
        self.assertQuerySetEqual(plan.activities.all(), [activity], transform=lambda item: item)
        self.assertQuerySetEqual(plan.readings.all(), [reading], transform=lambda item: item)
        self.assertEqual(set(plan.games.all()), {game_one, game_two})
        self.assertTrue(plan.assignments.filter(student=self.linked_student).exists())

    def test_lesson_plan_form_filters_resources_by_grade_subject_and_level(self):
        other_level = Level.objects.create(number=2, name='Intermedio', order=2)
        other_subject = Subject.objects.create(name='Matemática')
        matching_activity = Activity.objects.create(level=self.level, subject=self.subject, grade='1', title='Actividad visible', activity_type=Activity.ActivityType.READING)
        Activity.objects.create(level=other_level, subject=self.subject, grade='1', title='Actividad otro nivel', activity_type=Activity.ActivityType.READING)
        matching_reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura visible', content='Texto')
        Reading.objects.create(level=self.level, subject=other_subject, grade='1', title='Lectura otra materia', content='Texto')
        matching_game = Game.objects.create(level=self.level, subject=self.subject, grade='1', name='Juego visible', slug='juego-visible-plan', description='Juego', skill='Lectura', game_type=Game.GameType.DYSLEXIA_QUIZ)
        general_game = Game.objects.create(level=self.level, subject=self.subject, grade='', name='Juego general visible', slug='juego-general-visible-plan', description='Juego', skill='Lectura', game_type=Game.GameType.MEMORY)
        Game.objects.create(level=self.level, subject=self.subject, grade='2', name='Juego otro grado', slug='juego-otro-grado-plan', description='Juego', skill='Lectura', game_type=Game.GameType.MEMORY)

        form = LessonPlanForm(data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': 'Plan filtrado',
            'topic': 'Lectura',
            'objective': 'Leer mejor.',
        }, teacher=self.teacher)

        self.assertIn(matching_activity, form.fields['activities'].queryset)
        self.assertNotIn('Actividad otro nivel', form.fields['activities'].queryset.values_list('title', flat=True))
        self.assertIn(matching_reading, form.fields['readings'].queryset)
        self.assertNotIn('Lectura otra materia', form.fields['readings'].queryset.values_list('title', flat=True))
        self.assertIn(matching_game, form.fields['games'].queryset)
        self.assertIn(general_game, form.fields['games'].queryset)
        self.assertNotIn('Juego otro grado', form.fields['games'].queryset.values_list('name', flat=True))

    def test_lesson_plan_assignment_with_history_is_not_silently_deleted(self):
        self.teacher.can_edit_lesson_plans = True
        self.teacher.save(update_fields=['can_edit_lesson_plans'])
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan historial asignacion', topic='Seguimiento', objective='Conservar seguimiento.')
        completed_at = timezone.now()
        assignment = LessonPlanAssignment.objects.create(
            plan=plan,
            student=self.linked_student,
            status=LessonPlanAssignment.Status.IN_PROGRESS,
            completed_at=completed_at,
            teacher_notes='Necesita apoyo con lectura guiada.',
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_update', args=[plan.pk]), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': plan.title,
            'topic': plan.topic,
            'objective': plan.objective,
            'assigned_students': [],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('dashboard:lesson_plans'))
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        self.assertEqual(assignment.status, LessonPlanAssignment.Status.IN_PROGRESS)
        self.assertEqual(assignment.teacher_notes, 'Necesita apoyo con lectura guiada.')
        self.assertEqual(assignment.completed_at, completed_at)

    def test_unused_lesson_plan_assignment_can_be_removed(self):
        self.teacher.can_edit_lesson_plans = True
        self.teacher.save(update_fields=['can_edit_lesson_plans'])
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan sin uso asignacion', topic='Seguimiento', objective='Remover asignacion sin uso.')
        assignment = LessonPlanAssignment.objects.create(plan=plan, student=self.linked_student)
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_update', args=[plan.pk]), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': plan.title,
            'topic': plan.topic,
            'objective': plan.objective,
            'assigned_students': [],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('dashboard:lesson_plans'))
        self.assertFalse(LessonPlanAssignment.objects.filter(pk=assignment.pk).exists())

    def test_new_lesson_plan_assignment_is_active(self):
        self.teacher.can_edit_lesson_plans = True
        self.teacher.save(update_fields=['can_edit_lesson_plans'])
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan asignacion activa', topic='Seguimiento', objective='Crear asignacion activa.')
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_update', args=[plan.pk]), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': plan.title,
            'topic': plan.topic,
            'objective': plan.objective,
            'assigned_students': [self.linked_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('dashboard:lesson_plans'))
        self.assertTrue(LessonPlanAssignment.objects.get(plan=plan, student=self.linked_student).is_active)

    def test_inactive_assignment_does_not_appear_as_current_student_class(self):
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan historico oculto', topic='Seguimiento', objective='No mostrar vigente.')
        LessonPlanAssignment.objects.create(plan=plan, student=self.linked_student, is_active=False, status=LessonPlanAssignment.Status.IN_PROGRESS, teacher_notes='Historial')
        self.client.force_login(self.linked_user)

        dashboard_response = self.client.get(reverse('dashboard:student'))
        detail_response = self.client.get(reverse('dashboard:student_lesson_plan', args=[plan.pk]))

        self.assertNotContains(dashboard_response, 'Plan historico oculto')
        self.assertEqual(detail_response.status_code, 404)

    def test_reassigning_inactive_assignment_reactivates_without_duplicate(self):
        self.teacher.can_edit_lesson_plans = True
        self.teacher.save(update_fields=['can_edit_lesson_plans'])
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan reactivado', topic='Seguimiento', objective='Reactivar asignacion.')
        assignment = LessonPlanAssignment.objects.create(plan=plan, student=self.linked_student, is_active=False, status=LessonPlanAssignment.Status.IN_PROGRESS, teacher_notes='Historial previo')
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_update', args=[plan.pk]), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': plan.title,
            'topic': plan.topic,
            'objective': plan.objective,
            'assigned_students': [self.linked_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertRedirects(response, reverse('dashboard:lesson_plans'))
        assignment.refresh_from_db()
        self.assertTrue(assignment.is_active)
        self.assertEqual(assignment.teacher_notes, 'Historial previo')
        self.assertEqual(LessonPlanAssignment.objects.filter(plan=plan, student=self.linked_student).count(), 1)

    def test_historical_assignments_remain_in_database(self):
        plan = LessonPlan.objects.create(teacher=self.teacher, subject=self.subject, level=self.level, grade='1', title='Plan historico permanece', topic='Seguimiento', objective='Permanecer en base.')
        assignment = LessonPlanAssignment.objects.create(plan=plan, student=self.linked_student, is_active=False, status=LessonPlanAssignment.Status.COMPLETED, teacher_notes='Historial')

        self.assertTrue(LessonPlanAssignment.objects.filter(pk=assignment.pk, is_active=False).exists())

    def test_teacher_cannot_assign_resources_from_another_grade_by_post(self):
        other_grade_activity = Activity.objects.create(
            level=self.level,
            subject=self.subject,
            grade='2',
            title='Actividad de otro grado',
            activity_type=Activity.ActivityType.READING,
        )
        other_grade_reading = Reading.objects.create(
            level=self.level,
            subject=self.subject,
            grade='2',
            title='Lectura de otro grado',
            content='Texto de otro grado.',
        )
        other_grade_game = Game.objects.create(
            level=self.level,
            subject=self.subject,
            grade='2',
            name='Juego de otro grado',
            slug='juego-de-otro-grado-post',
            description='Juego fuera del grado',
            skill='Lectura',
            game_type=Game.GameType.MEMORY,
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_create'), data={
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': 'Plan con recursos manipulados',
            'topic': 'Lectura',
            'objective': 'Evitar recursos de otro grado.',
            'activities': [other_grade_activity.pk],
            'readings': [other_grade_reading.pk],
            'games': [other_grade_game.pk],
            'assigned_students': [self.linked_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escoja una opción válida')
        self.assertFalse(LessonPlan.objects.filter(title='Plan con recursos manipulados').exists())

    def test_teacher_cannot_select_competency_from_another_grade_by_post(self):
        other_grade_competency = CurriculumCompetency.objects.create(
            subject=self.subject,
            grade='2',
            title='Competencia de segundo grado',
            competency='Contenido de segundo grado.',
            achievement_indicator='Indicador de segundo grado.',
        )
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:lesson_plan_create'), data={
            'subject': self.subject.pk,
            'competency': other_grade_competency.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': 'Plan con competencia manipulada',
            'topic': 'Lectura',
            'objective': 'Evitar competencia de otro grado.',
            'assigned_students': [self.linked_student.pk],
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Escoja una opción válida')
        self.assertFalse(LessonPlan.objects.filter(title='Plan con competencia manipulada').exists())

    def test_existing_lesson_plan_without_closing_or_games_still_works(self):
        self.teacher.can_assign_lesson_plans = True
        self.teacher.save(update_fields=['can_assign_lesson_plans'])
        plan = LessonPlan.objects.create(
            teacher=self.teacher,
            subject=self.subject,
            level=self.level,
            grade='1',
            title='Plan antiguo',
            topic='Comprensión',
            objective='Comprender textos breves.',
        )
        self.client.force_login(self.teacher_user)

        response = self.client.get(reverse('dashboard:lesson_plan_implementation', args=[plan.pk]))

        self.assertEqual(plan.closing_activities, '')
        self.assertEqual(plan.games.count(), 0)
        self.assertContains(response, 'Plan antiguo')
        self.assertContains(response, 'Retoma el indicador de logro')
        self.assertContains(response, 'No hay juegos vinculados todavía.')

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

    def test_parent_navigation_hides_student_options(self):
        parent_user = CustomUser.objects.create_user(
            username='padrenav',
            email='padrenav@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Nav')
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:parents'))

        html = response.content.decode()
        nav_html = html.split('<main class="page-shell">', 1)[0]
        self.assertIn('Panel familiar', nav_html)
        self.assertIn('Mi panel', nav_html)
        self.assertIn('Perfil', nav_html)
        self.assertIn('Cerrar sesión', nav_html)
        self.assertNotIn(f'href="{reverse("learning:levels")}"', nav_html)
        self.assertNotIn(f'href="{reverse("activities:list")}"', nav_html)
        self.assertNotIn(f'href="{reverse("games:index")}"', nav_html)
        self.assertNotIn(f'href="{reverse("readings:list")}"', nav_html)
        self.assertNotIn(f'href="{reverse("progress:overview")}"', nav_html)
        self.assertNotIn(f'href="{reverse("learning:accessibility")}"', nav_html)

    def test_parent_home_is_oriented_to_family_dashboard(self):
        parent_user = CustomUser.objects.create_user(
            username='padreinicio',
            email='padreinicio@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Inicio')
        self.client.force_login(parent_user)

        response = self.client.get(reverse('core:home'))

        self.assertContains(response, 'Ir a mi Panel familiar')
        self.assertContains(response, 'Ver progreso de mis estudiantes')
        self.assertContains(response, 'Nivel 1')
        self.assertNotContains(response, f'href="{reverse("learning:level_detail", args=[1])}"')
        self.assertNotContains(response, 'Ir a Aprender')
        self.assertNotContains(response, 'Ir a Practicar')
        self.assertNotContains(response, 'Ver avance')

    def test_parent_login_redirect_goes_to_family_dashboard(self):
        parent_user = CustomUser.objects.create_user(
            username='padredirect',
            email='padredirect@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Redirect')
        self.client.force_login(parent_user)

        response = self.client.get(reverse('dashboard:redirect'))

        self.assertRedirects(response, reverse('dashboard:parents'))

    def test_parent_cannot_register_activity_attempt(self):
        parent_user = CustomUser.objects.create_user(
            username='padreactividad',
            email='padreactividad@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Actividad')
        activity = Activity.objects.create(
            level=self.level,
            subject=self.subject,
            grade='1',
            title='Actividad familiar',
            activity_type=Activity.ActivityType.LISTEN_SELECT,
            is_active=True,
        )
        option = ActivityOption.objects.create(activity=activity, text='Casa', is_correct=True)
        self.client.force_login(parent_user)

        response = self.client.post(reverse('activities:submit_answer', args=[activity.pk]), {'option_id': option.pk})

        self.assertRedirects(response, reverse('activities:detail', args=[activity.pk]))
        self.assertEqual(ActivityAttempt.objects.count(), 0)

    def test_parent_cannot_create_reading_progress_or_answers(self):
        parent_user = CustomUser.objects.create_user(
            username='padrelectura',
            email='padrelectura@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Lectura')
        reading = Reading.objects.create(
            title='Lectura familiar',
            content='Una lectura breve.',
            level=self.level,
            subject=self.subject,
            grade='1',
            is_active=True,
        )
        question = ReadingQuestion.objects.create(reading=reading, question='Pregunta')
        answer = ReadingAnswer.objects.create(question=question, answer='Respuesta', is_correct=True)
        self.client.force_login(parent_user)

        detail_response = self.client.get(reverse('readings:detail', args=[reading.pk]))
        save_response = self.client.post(
            reverse('readings:save_comprehension_answer', args=[reading.pk]),
            data=json.dumps({'question_id': question.pk, 'answer_id': answer.pk, 'completed': True}),
            content_type='application/json',
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertEqual(save_response.status_code, 403)
        self.assertEqual(ReadingProgress.objects.count(), 0)
        self.assertEqual(ReadingComprehensionAnswer.objects.count(), 0)

    def test_parent_cannot_create_game_attempt(self):
        parent_user = CustomUser.objects.create_user(
            username='padrejuego',
            email='padrejuego@example.com',
            password='Padre12345!',
            role=CustomUser.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent_user, name='Padre Juego')
        game = Game.objects.create(
            name='Juego familiar',
            slug='juego-familiar',
            description='Juego de prueba.',
            skill='Lectura',
            game_type=Game.GameType.DYSLEXIA_QUIZ,
            level=self.level,
            subject=self.subject,
            grade='1',
            is_active=True,
        )
        self.client.force_login(parent_user)

        response = self.client.post(
            reverse('games:save_attempt', args=[game.slug]),
            data=json.dumps({'total_questions': 1, 'correct_answers': 1, 'completed': True, 'answers': []}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(GameAttempt.objects.count(), 0)

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


class CreationAndDeletionAtomicityTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')

    def test_failing_parent_creation_leaves_no_orphan_student(self):
        form = QuickStudentCreationForm(data={
            'name': 'Hugo Orfano',
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'new_parent_first_name': 'Ana',
            'new_parent_last_name': 'Orfano',
            'new_parent_email': 'ana.orfano@example.com',
        })
        self.assertTrue(form.is_valid(), form.errors)

        with patch('dashboard.forms.ParentProfile.objects.create', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                form.save()

        self.assertFalse(StudentProfile.objects.filter(name='Hugo Orfano').exists())
        self.assertFalse(CustomUser.objects.filter(username='hugo_orfano').exists())
        self.assertFalse(CustomUser.objects.filter(email='ana.orfano@example.com').exists())

    def test_protected_delete_leaves_no_audit_row(self):
        from core.models import AuditLog
        from django.db.models.deletion import ProtectedError

        admin = CustomUser.objects.create_user(username='adminprotegido', email='adminprotegido@example.com', password='Admin12345!', role=CustomUser.Role.ADMIN, is_staff=True)
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura protegida', content='Texto.', is_active=True)
        self.client.force_login(admin)

        with patch.object(Reading, 'delete', side_effect=ProtectedError('protegido', set())):
            response = self.client.post(reverse('dashboard:admin_resource_delete', args=['lecturas', reading.pk]))

        self.assertRedirects(response, reverse('dashboard:admin_resource', args=['lecturas']))
        self.assertTrue(Reading.objects.filter(pk=reading.pk).exists())
        self.assertFalse(AuditLog.objects.filter(action='delete', model_name='Reading').exists())

    def test_successful_delete_writes_audit_with_original_id(self):
        from core.models import AuditLog

        admin = CustomUser.objects.create_user(username='adminborra', email='adminborra@example.com', password='Admin12345!', role=CustomUser.Role.ADMIN, is_staff=True)
        reading = Reading.objects.create(level=self.level, subject=self.subject, grade='1', title='Lectura borrable', content='Texto.', is_active=True)
        reading_pk = reading.pk
        self.client.force_login(admin)

        self.client.post(reverse('dashboard:admin_resource_delete', args=['lecturas', reading_pk]))

        self.assertFalse(Reading.objects.filter(pk=reading_pk).exists())
        log = AuditLog.objects.get(action='delete', model_name='Reading')
        self.assertEqual(log.object_id, str(reading_pk))
        self.assertEqual(log.object_repr, 'Lectura borrable')


class PlanTeacherAndTutorCredentialTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.admin = CustomUser.objects.create_user(username='adminplanes', email='adminplanes@example.com', password='Admin12345!', role=CustomUser.Role.ADMIN, is_staff=True)
        self.first_teacher = TeacherProfile.objects.create(name='Docente Primero')
        self.teacher_user = CustomUser.objects.create_user(username='docenteelegido', email='docenteelegido@example.com', password='Docente123!', role=CustomUser.Role.TEACHER)
        self.teacher = TeacherProfile.objects.create(user=self.teacher_user, name='Docente Elegido', can_create_students=True, can_create_lesson_plans=True)
        self.inactive_teacher = TeacherProfile.objects.create(name='Docente Inactivo', is_active=False)

    def plan_data(self, title, **extra):
        data = {
            'subject': self.subject.pk,
            'level': self.level.pk,
            'grade': '1',
            'title': title,
            'topic': 'Lectura',
            'objective': 'Leer.',
            'status': LessonPlan.Status.ACTIVE,
            'is_active': 'on',
        }
        data.update(extra)
        return data

    def test_admin_creates_plan_for_chosen_teacher(self):
        self.client.force_login(self.admin)

        self.client.post(reverse('dashboard:lesson_plan_create'), data=self.plan_data('Plan elegido', plan_teacher=self.teacher.pk))

        self.assertEqual(LessonPlan.objects.get(title='Plan elegido').teacher, self.teacher)

    def test_admin_must_choose_an_active_teacher(self):
        self.client.force_login(self.admin)

        missing = self.client.post(reverse('dashboard:lesson_plan_create'), data=self.plan_data('Plan sin docente'))
        inactive = self.client.post(reverse('dashboard:lesson_plan_create'), data=self.plan_data('Plan inactivo', plan_teacher=self.inactive_teacher.pk))

        self.assertEqual(missing.status_code, 200)
        self.assertEqual(inactive.status_code, 200)
        self.assertFalse(LessonPlan.objects.filter(title__in=['Plan sin docente', 'Plan inactivo']).exists())

    def test_teacher_cannot_pick_another_teacher(self):
        self.client.force_login(self.teacher_user)

        self.client.post(reverse('dashboard:lesson_plan_create'), data=self.plan_data('Plan propio', plan_teacher=self.first_teacher.pk))

        self.assertEqual(LessonPlan.objects.get(title='Plan propio').teacher, self.teacher)

    def student_with_new_tutor(self, name, email):
        return {
            'name': name,
            'grade': '1',
            'school': 'public',
            'modality': 'regular',
            'zone': 'urban',
            'reading_level': self.level.pk,
            'new_parent_first_name': 'Laura',
            'new_parent_last_name': 'Tutora',
            'new_parent_email': email,
        }

    def test_teacher_sees_new_tutor_password_once_and_it_authenticates(self):
        import re
        from django.contrib.auth import authenticate

        self.client.force_login(self.teacher_user)
        response = self.client.post(reverse('dashboard:teacher_students'), data=self.student_with_new_tutor('Alumno Con Tutora', 'laura.tutora@example.com'), follow=True)

        text = ' '.join(str(message) for message in response.context['messages'])
        match = re.search(r'Tutor: (\S+) / Contraseña: (\S+)', text)
        self.assertIsNotNone(match, text)
        username, password = match.groups()
        self.assertEqual(CustomUser.objects.get(email='laura.tutora@example.com').username, username)
        self.assertIsNotNone(authenticate(username=username, password=password))

        again = self.client.get(reverse('dashboard:teacher_students'))
        self.assertNotContains(again, password)

    def test_quick_student_page_shows_new_tutor_credentials(self):
        self.client.force_login(self.teacher_user)

        response = self.client.post(reverse('dashboard:quick_student_create'), data=self.student_with_new_tutor('Alumno Rapido', 'tutora.rapida@example.com'))

        tutor = CustomUser.objects.get(email='tutora.rapida@example.com')
        self.assertContains(response, tutor.username)
        self.assertContains(response, 'Contraseña del tutor')


class StudentReportQueryCountTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.admin = CustomUser.objects.create_user(username='adminreporte', email='adminreporte@example.com', password='Admin12345!', role=CustomUser.Role.ADMIN, is_staff=True)
        user = CustomUser.objects.create_user(username='alumnoreporte', email='alumnoreporte@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        self.student = StudentProfile.objects.create(user=user, name='Alumno Reporte Consultas', grade='1', reading_level=self.level, current_level=self.level)
        self.counter = 0

    def add_reading_row(self):
        self.counter += 1
        reading = Reading.objects.create(level=self.level, grade='1', title=f'Lectura {self.counter}', content='Texto.')
        question = ReadingQuestion.objects.create(reading=reading, question='¿Qué pasó?')
        ReadingQuestion.objects.create(reading=reading, question='¿Quién fue?')
        ReadingProgress.objects.create(student=self.student, reading=reading)
        ReadingComprehensionAnswer.objects.create(student=self.student, reading=reading, question=question, selected_answer='Algo', is_correct=True)

    def report_query_count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(reverse('dashboard:student_report', args=[self.student.pk]))
        self.assertEqual(response.status_code, 200)
        return len(queries), response

    def test_query_count_does_not_grow_with_reading_rows(self):
        self.client.force_login(self.admin)
        self.add_reading_row()
        one_row_queries, _ = self.report_query_count()
        for _ in range(4):
            self.add_reading_row()

        many_rows_queries, response = self.report_query_count()

        self.assertEqual(many_rows_queries, one_row_queries)
        row = response.context['reading_rows'][0]
        self.assertEqual(row['total_questions'], 2)
        self.assertEqual(row['answered_questions'], 1)
        self.assertEqual(row['correct_answers'], 1)


class ResourceListPaginationTests(TestCase):
    """Bodega-style server pagination (10 per page) and GET search on list tables."""

    def setUp(self):
        self.admin = CustomUser.objects.create_user(
            username='adminpaginas',
            email='adminpaginas@example.com',
            password='Admin12345!',
            role=CustomUser.Role.ADMIN,
            is_staff=True,
        )
        for number in range(1, 26):
            CustomUser.objects.create_user(
                username=f'pgu{number:02d}x',
                email=f'pgu{number:02d}x@example.com',
                password=None,
                role=CustomUser.Role.PARENT,
            )
        self.client.force_login(self.admin)
        self.url = reverse('dashboard:admin_resource', args=['usuarios'])

    def test_first_page_shows_ten_newest_records(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj'].object_list), 10)
        self.assertContains(response, 'pgu25x')
        self.assertContains(response, 'pgu16x')
        self.assertNotContains(response, 'pgu15x')
        self.assertContains(response, 'Mostrando 1 a 10 de 26 registros')

    def test_second_page_shows_records_eleven_to_twenty(self):
        response = self.client.get(self.url, {'page': 2})

        self.assertContains(response, 'pgu15x')
        self.assertContains(response, 'pgu06x')
        self.assertNotContains(response, 'pgu16x')
        self.assertNotContains(response, 'pgu05x')
        self.assertContains(response, 'Mostrando 11 a 20 de 26 registros')
        # Dialogs are rendered for the rows on the current page.
        row_user = CustomUser.objects.get(username='pgu15x')
        self.assertContains(response, f'editResourceModal{row_user.pk}"')
        self.assertContains(response, f'deleteResourceModal{row_user.pk}"')

    def test_search_filters_server_side_and_is_kept_in_pagination_links(self):
        for number in range(1, 13):
            CustomUser.objects.create_user(
                username=f'buscable{number:02d}',
                email=f'buscable{number:02d}@example.com',
                password=None,
                role=CustomUser.Role.PARENT,
            )

        response = self.client.get(self.url, {'q': 'buscable'})

        self.assertContains(response, 'Mostrando 1 a 10 de 12 registros')
        self.assertNotContains(response, 'pgu25x')
        self.assertContains(response, 'value="buscable"')
        self.assertContains(response, '?q=buscable&amp;page=2')

    def test_invalid_or_out_of_range_page_does_not_fail(self):
        for page in ('abc', '999', '-1'):
            response = self.client.get(self.url, {'page': page})
            self.assertEqual(response.status_code, 200)

    def test_teacher_students_list_is_paginated(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        teacher_user = CustomUser.objects.create_user(
            username='docentepaginas',
            email='docentepaginas@example.com',
            password='Docente123!',
            role=CustomUser.Role.TEACHER,
        )
        teacher = TeacherProfile.objects.create(user=teacher_user, name='Docente Paginas')
        for number in range(1, 13):
            user = CustomUser.objects.create_user(
                username=f'alpag{number:02d}',
                email=f'alpag{number:02d}@example.com',
                password=None,
                role=CustomUser.Role.STUDENT,
            )
            teacher.students.add(StudentProfile.objects.create(
                user=user, name=f'Alumno Pag {number:02d}', grade='1', reading_level=level, current_level=level,
            ))
        self.client.force_login(teacher_user)

        response = self.client.get(reverse('dashboard:teacher_students'), {'page': 2})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Alumno Pag 11')
        self.assertNotContains(response, 'Alumno Pag 10')
        self.assertContains(response, 'Mostrando 11 a 12 de 12 registros')
