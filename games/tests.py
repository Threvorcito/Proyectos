import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from learning.models import Level, StudentProfile, Subject

from .models import Game, GameAttempt
from .services import ensure_games, get_recommended_games


class GameAttemptSaveTests(TestCase):
    def test_save_attempt_handles_invalid_numbers_without_server_error(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        user = CustomUser.objects.create_user(
            username='estudiantequiz',
            email='estudiantequiz@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user, name='Estudiante Quiz', grade='1', current_level=level, reading_level=level)
        game = Game.objects.create(
            level=level,
            subject=subject,
            grade='1',
            name='Quiz de agilidad lectora',
            slug='quiz-prueba',
            description='Prueba',
            skill='Agilidad lectora',
            game_type=Game.GameType.DYSLEXIA_QUIZ,
        )
        self.client.force_login(user)

        response = self.client.post(
            reverse('games:save_attempt', args=[game.slug]),
            data=json.dumps({'total_questions': 'abc', 'correct_answers': '99'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        attempt = GameAttempt.objects.get(game=game)
        self.assertEqual(attempt.total_questions, 0)
        self.assertEqual(attempt.correct_answers, 0)
        self.assertEqual(attempt.score, 0)


class GameStudentExperienceTests(TestCase):
    def test_student_games_page_hides_grade_filters(self):
        level = Level.objects.create(number=1, name='Inicial', order=1)
        subject = Subject.objects.create(name='Lengua y Literatura')
        user = CustomUser.objects.create_user(
            username='estudiantejuegos',
            email='estudiantejuegos@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        StudentProfile.objects.create(user=user, name='Estudiante Juegos', grade='1', current_level=level, reading_level=level)
        Game.objects.create(level=level, subject=subject, grade='1', name='Juego grado 1', slug='juego-grado-1', description='Juego', skill='Lectura', game_type=Game.GameType.DYSLEXIA_QUIZ)
        Game.objects.create(level=level, subject=subject, grade='2', name='Juego grado 2', slug='juego-grado-2', description='Juego', skill='Lectura', game_type=Game.GameType.DYSLEXIA_QUIZ)
        self.client.force_login(user)

        response = self.client.get(reverse('games:index'), {'grade': '2'})

        self.assertContains(response, 'Juegos para tu grado')
        self.assertContains(response, 'Juego grado 1')
        self.assertNotContains(response, 'Juego grado 2')
        self.assertNotContains(response, 'activity-filter-board')


class GameGradeFilterTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial', order=1)
        self.subject = Subject.objects.create(name='Lengua y Literatura')
        self.students = {}
        for grade in ('1', '2', '3'):
            user = CustomUser.objects.create_user(
                username=f'jugador{grade}',
                email=f'jugador{grade}@example.com',
                password='Demo12345!',
                role=CustomUser.Role.STUDENT,
            )
            self.students[grade] = StudentProfile.objects.create(user=user, name=f'Jugador {grade}', grade=grade, current_level=self.level, reading_level=self.level)
            Game.objects.create(
                level=self.level,
                subject=self.subject,
                grade=grade,
                name=f'Juego grado {grade}',
                slug=f'juego-grado-{grade}',
                description='Juego de prueba',
                skill='Lectura',
                game_type=Game.GameType.DYSLEXIA_QUIZ,
            )
        self.general_game = Game.objects.create(
            level=self.level,
            subject=self.subject,
            grade='',
            name='Juego general',
            slug='juego-general',
            description='Juego publico para todos',
            skill='Practica general',
            game_type=Game.GameType.DYSLEXIA_QUIZ,
        )

    def test_students_see_only_their_grade_plus_general_games(self):
        for grade, student in self.students.items():
            self.client.force_login(student.user)
            response = self.client.get(reverse('games:index'), {'grade': '3' if grade != '3' else '1'})
            self.assertContains(response, f'Juego grado {grade}')
            self.assertContains(response, 'Juego general')
            for other_grade in {'1', '2', '3'} - {grade}:
                self.assertNotContains(response, f'Juego grado {other_grade}')

    def test_grade_specific_games_are_visible_only_to_matching_grade(self):
        for visible_grade, student in self.students.items():
            self.client.force_login(student.user)
            response = self.client.get(reverse('games:index'))
            for game_grade in ('1', '2', '3'):
                assertion = self.assertContains if game_grade == visible_grade else self.assertNotContains
                assertion(response, f'Juego grado {game_grade}')

    def test_general_game_visible_and_openable_for_all_grades(self):
        for student in self.students.values():
            self.client.force_login(student.user)
            list_response = self.client.get(reverse('games:index'))
            detail_response = self.client.get(reverse('games:detail', args=[self.general_game.slug]))

            self.assertContains(list_response, 'Juego general')
            self.assertEqual(detail_response.status_code, 200)

    def test_student_cannot_open_game_from_other_grade(self):
        self.client.force_login(self.students['1'].user)

        response = self.client.get(reverse('games:detail', args=['juego-grado-2']))

        self.assertEqual(response.status_code, 404)

    def test_student_cannot_save_attempt_for_game_from_other_grade(self):
        self.client.force_login(self.students['1'].user)

        response = self.client.post(
            reverse('games:save_attempt', args=['juego-grado-2']),
            data=json.dumps({'total_questions': 1, 'correct_answers': 1}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)


class QuizAgilidadLectoraGeneralTests(TestCase):
    def setUp(self):
        for number in (1, 2, 3):
            Level.objects.create(number=number, name=f'Nivel {number}', order=number)
        Subject.objects.create(name='Lengua y Literatura')
        self.students = {}
        for grade in ('1', '2', '3'):
            user = CustomUser.objects.create_user(
                username=f'quizjugador{grade}',
                email=f'quizjugador{grade}@example.com',
                password='Demo12345!',
                role=CustomUser.Role.STUDENT,
            )
            level = Level.objects.get(number=int(grade))
            self.students[grade] = StudentProfile.objects.create(user=user, name=f'Quiz Jugador {grade}', grade=grade, current_level=level, reading_level=level)
        ensure_games()

    def test_quiz_agilidad_lectora_is_general(self):
        quiz = Game.objects.get(slug='quiz-agilidad-lectora')

        self.assertEqual(quiz.grade, '')

    def test_quiz_agilidad_lectora_visible_and_openable_for_all_grades(self):
        for student in self.students.values():
            self.client.force_login(student.user)
            list_response = self.client.get(reverse('games:index'))
            detail_response = self.client.get(reverse('games:detail', args=['quiz-agilidad-lectora']))

            self.assertContains(list_response, 'Quiz de agilidad lectora')
            self.assertEqual(detail_response.status_code, 200)

    def test_quiz_agilidad_lectora_can_be_recommended_when_selected_by_level(self):
        for grade in ('2', '3'):
            recommended_slugs = {game.slug for game in get_recommended_games(self.students[grade])}

            self.assertIn('quiz-agilidad-lectora', recommended_slugs)
