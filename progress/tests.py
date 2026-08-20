from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from activities.models import Activity
from learning.models import Level, StudentProfile
from progress.models import StudentDifficulty
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
