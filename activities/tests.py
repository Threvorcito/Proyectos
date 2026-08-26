from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from learning.models import Level, StudentProfile
from progress.models import ActivityAttempt, StudentDifficulty

from .models import Activity, ActivityOption
from .services import get_recommended_activities


class ActivitySubmissionTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.user = CustomUser.objects.create_user(
            username='estudiante',
            email='estudiante@example.com',
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
        self.activity = Activity.objects.create(
            level=self.level,
            title='Elige la vocal',
            activity_type=Activity.ActivityType.LISTEN_SELECT,
            points=10,
            stars=1,
        )
        self.correct = ActivityOption.objects.create(activity=self.activity, text='A', is_correct=True)
        self.incorrect = ActivityOption.objects.create(activity=self.activity, text='B', is_correct=False)

    def test_submission_uses_database_option_not_tampered_payload(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('activities:submit_answer', args=[self.activity.pk]),
            {'option_id': self.incorrect.pk, 'answer': self.correct.text, 'is_correct': '1'},
        )

        self.assertRedirects(response, reverse('activities:detail', args=[self.activity.pk]))
        attempt = ActivityAttempt.objects.get()
        self.assertEqual(attempt.answer, self.incorrect.text)
        self.assertFalse(attempt.is_correct)

    def test_non_student_cannot_register_activity_attempt(self):
        teacher = CustomUser.objects.create_user(
            username='docente',
            email='docente@example.com',
            password='Demo12345!',
            role=CustomUser.Role.TEACHER,
        )
        self.client.force_login(teacher)
        response = self.client.post(
            reverse('activities:submit_answer', args=[self.activity.pk]),
            {'option_id': self.correct.pk},
        )

        self.assertRedirects(response, reverse('activities:detail', args=[self.activity.pk]))
        self.assertEqual(ActivityAttempt.objects.count(), 0)

    def test_recommendations_use_student_letter_difficulty(self):
        letter_activity = Activity.objects.create(
            level=self.level,
            title='Letras parecidas',
            activity_type=Activity.ActivityType.SIMILAR_LETTERS,
            grade=StudentProfile.Grade.FIRST,
        )
        Activity.objects.create(
            level=self.level,
            title='Lectura general',
            activity_type=Activity.ActivityType.READING,
            grade=StudentProfile.Grade.FIRST,
        )
        StudentDifficulty.objects.create(
            student=self.student,
            difficulty_type='letter_confusion',
            character_a='b',
            character_b='d',
            error_count=3,
        )

        recommendations = list(get_recommended_activities(self.student))

        self.assertIn(letter_activity, recommendations)
        self.assertTrue(all(activity.activity_type in ('FIND_LETTER', 'SIMILAR_LETTERS') for activity in recommendations))


class ActivityGradeFilterTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.students = {}
        for grade in ('1', '2', '3'):
            user = CustomUser.objects.create_user(
                username=f'estudiante{grade}',
                email=f'estudiante{grade}@example.com',
                password='Demo12345!',
                role=CustomUser.Role.STUDENT,
            )
            self.students[grade] = StudentProfile.objects.create(user=user, name=f'Estudiante {grade}', grade=grade, reading_level=self.level, current_level=self.level)
            Activity.objects.create(level=self.level, title=f'Actividad grado {grade}', activity_type=Activity.ActivityType.READING, grade=grade)

    def test_students_only_see_activities_for_their_grade(self):
        for grade, student in self.students.items():
            self.client.force_login(student.user)
            response = self.client.get(reverse('activities:list'), {'grade': '3' if grade != '3' else '1'})
            self.assertContains(response, f'Actividad grado {grade}')
            for other_grade in {'1', '2', '3'} - {grade}:
                self.assertNotContains(response, f'Actividad grado {other_grade}')

    def test_student_cannot_open_activity_from_other_grade(self):
        self.client.force_login(self.students['1'].user)
        other_activity = Activity.objects.get(title='Actividad grado 2')

        response = self.client.get(reverse('activities:detail', args=[other_activity.pk]))

        self.assertEqual(response.status_code, 404)

    def test_recommendations_do_not_fallback_to_other_grades_without_general_marker(self):
        level = Level.objects.create(number=2, name='Intermedio')
        user = CustomUser.objects.create_user(username='singeneral', email='singeneral@example.com', password='Demo12345!', role=CustomUser.Role.STUDENT)
        student = StudentProfile.objects.create(user=user, name='Sin General', grade='1', reading_level=level, current_level=level)
        Activity.objects.create(level=level, title='Solo segundo', activity_type=Activity.ActivityType.READING, grade='2')

        self.assertEqual(list(get_recommended_activities(student)), [])
