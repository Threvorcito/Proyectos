from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from activities.models import Activity
from learning.models import Level, StudentProfile
from progress.models import StudentDifficulty, StudentProgress
from progress.services import register_attempt


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


class DifficultyDetectionTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.user = CustomUser.objects.create_user(
            username='estudiante',
            email='estudiante-dificultad@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.user,
            name='Estudiante Demo',
            grade=StudentProfile.Grade.FIRST,
            reading_level=self.level,
            current_level=self.level,
        )

    def test_similar_letter_error_is_tracked_as_letter_confusion(self):
        activity = Activity.objects.create(
            level=self.level,
            title='Distingue b y d',
            activity_type=Activity.ActivityType.SIMILAR_LETTERS,
        )

        register_attempt(self.user, activity, answer='d', is_correct=False, correct_answer='b')

        difficulty = StudentDifficulty.objects.get(student=self.student)
        self.assertEqual(difficulty.difficulty_type, 'letter_confusion')
        self.assertEqual(difficulty.character_a, 'b')
        self.assertEqual(difficulty.character_b, 'd')

    def test_syllable_error_is_tracked_as_syllable_confusion(self):
        activity = Activity.objects.create(
            level=self.level,
            title='Forma la sílaba',
            activity_type=Activity.ActivityType.SYLLABLES,
        )

        register_attempt(self.user, activity, answer='pa', is_correct=False, correct_answer='ma')

        difficulty = StudentDifficulty.objects.get(student=self.student)
        self.assertEqual(difficulty.difficulty_type, 'syllable_confusion')
        self.assertEqual(difficulty.syllable, 'pa')


class AttemptScoringTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.user = CustomUser.objects.create_user(
            username='estudiantepuntos',
            email='estudiantepuntos@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(
            user=self.user,
            name='Estudiante Puntos',
            grade=StudentProfile.Grade.FIRST,
            reading_level=self.level,
            current_level=self.level,
        )
        self.activity = Activity.objects.create(
            level=self.level,
            title='Encuentra la b',
            description='Prueba',
            instructions='Elige',
            activity_type=Activity.ActivityType.FIND_LETTER,
            points=10,
            stars=1,
        )

    def test_repeating_a_correct_answer_awards_points_once(self):
        register_attempt(self.user, self.activity, 'b', True, 'b')
        register_attempt(self.user, self.activity, 'b', True, 'b')

        self.student.refresh_from_db()
        self.assertEqual(self.student.points, 10)
        self.assertEqual(self.student.stars, 1)
        self.assertEqual(self.student.experience, 10)

    def test_first_correct_answer_after_errors_awards_points(self):
        register_attempt(self.user, self.activity, 'd', False, 'b')
        register_attempt(self.user, self.activity, 'b', True, 'b')

        self.student.refresh_from_db()
        self.assertEqual(self.student.points, 10)

    def test_attempt_numbers_and_progress_counts_increase(self):
        register_attempt(self.user, self.activity, 'd', False, 'b')
        last = register_attempt(self.user, self.activity, 'd', False, 'b')

        self.assertEqual(last.attempt_number, 2)
        progress = StudentProgress.objects.get(student=self.student, activity=self.activity)
        self.assertEqual(progress.attempts, 2)
        self.assertEqual(StudentDifficulty.objects.get(student=self.student).error_count, 2)

    def test_duplicate_progress_rows_are_rejected(self):
        StudentProgress.objects.create(student=self.student, activity=self.activity)

        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentProgress.objects.create(student=self.student, activity=self.activity)

    def test_duplicate_difficulty_rows_are_rejected(self):
        StudentDifficulty.objects.create(student=self.student, difficulty_type='letter_confusion', character_a='b', character_b='d', word='d')

        with self.assertRaises(IntegrityError), transaction.atomic():
            StudentDifficulty.objects.create(student=self.student, difficulty_type='letter_confusion', character_a='b', character_b='d', word='d')
