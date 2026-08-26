import json

from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from gamification.models import Achievement, StudentAchievement
from gamification.services import evaluate_achievements
from learning.models import Level, StudentProfile

from .models import Reading, ReadingAnswer, ReadingComprehensionAnswer, ReadingProgress, ReadingQuestion


class ReadingGradeFilterTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.students = {}
        for grade in ('1', '2', '3'):
            user = CustomUser.objects.create_user(
                username=f'lector{grade}',
                email=f'lector{grade}@example.com',
                password='Demo12345!',
                role=CustomUser.Role.STUDENT,
            )
            self.students[grade] = StudentProfile.objects.create(user=user, name=f'Lector {grade}', grade=grade, reading_level=self.level, current_level=self.level)
            Reading.objects.create(level=self.level, title=f'Lectura grado {grade}', content='Texto breve.', grade=grade)

    def test_students_only_see_readings_for_their_grade(self):
        for grade, student in self.students.items():
            self.client.force_login(student.user)
            response = self.client.get(reverse('readings:list'), {'grade': '3' if grade != '3' else '1'})
            self.assertContains(response, f'Lectura grado {grade}')
            self.assertContains(response, 'Lecturas para tu grado')
            self.assertNotContains(response, 'activity-filter-board')
            for other_grade in {'1', '2', '3'} - {grade}:
                self.assertNotContains(response, f'Lectura grado {other_grade}')

    def test_student_cannot_open_reading_from_other_grade(self):
        self.client.force_login(self.students['1'].user)
        other_reading = Reading.objects.get(title='Lectura grado 2')

        response = self.client.get(reverse('readings:detail', args=[other_reading.pk]))

        self.assertEqual(response.status_code, 404)

    def test_reading_comprehension_keeps_answers_in_step_flow(self):
        reading = Reading.objects.get(title='Lectura grado 1')
        question = ReadingQuestion.objects.create(reading=reading, question='¿Quién sale en la lectura?')
        ReadingAnswer.objects.create(question=question, answer='Luna', is_correct=True)
        ReadingAnswer.objects.create(question=question, answer='Sol', is_correct=False)
        self.client.force_login(self.students['1'].user)

        response = self.client.get(reverse('readings:detail', args=[reading.pk]))

        self.assertContains(response, 'data-reading-comprehension')
        self.assertContains(response, '¿Quién sale en la lectura?')
        self.assertContains(response, 'data-reading-next')
        self.assertContains(response, 'data-correct="1"')
        self.assertContains(response, 'data-correct="0"')


class ReadingProgressRegistrationTests(TestCase):
    def setUp(self):
        self.level = Level.objects.create(number=1, name='Inicial')
        self.user = CustomUser.objects.create_user(
            username='lectorprogreso',
            email='lectorprogreso@example.com',
            password='Demo12345!',
            role=CustomUser.Role.STUDENT,
        )
        self.student = StudentProfile.objects.create(user=self.user, name='Lector Progreso', grade='1', reading_level=self.level, current_level=self.level)
        self.reading = Reading.objects.create(level=self.level, title='Lectura con progreso', content='Texto breve.', grade='1')
        self.question_one = ReadingQuestion.objects.create(reading=self.reading, question='¿Qué leyó?')
        self.question_two = ReadingQuestion.objects.create(reading=self.reading, question='¿Cómo leyó?')
        self.correct_one = ReadingAnswer.objects.create(question=self.question_one, answer='Texto', is_correct=True)
        self.incorrect_one = ReadingAnswer.objects.create(question=self.question_one, answer='Mapa', is_correct=False)
        self.correct_two = ReadingAnswer.objects.create(question=self.question_two, answer='Con calma', is_correct=True)
        self.incorrect_two = ReadingAnswer.objects.create(question=self.question_two, answer='Corriendo', is_correct=False)

    def post_answer(self, question, answer, completed=False):
        return self.client.post(
            reverse('readings:save_comprehension_answer', args=[self.reading.pk]),
            data=json.dumps({'question_id': question.pk, 'answer_id': answer.pk, 'completed': completed}),
            content_type='application/json',
        )

    def test_reading_started_when_student_opens_detail(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('readings:detail', args=[self.reading.pk]))

        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(student=self.student, reading=self.reading)
        self.assertFalse(progress.completed)
        self.assertEqual(progress.comprehension_percentage, 0)

    def test_correct_comprehension_answer_is_saved(self):
        self.client.force_login(self.user)

        response = self.post_answer(self.question_one, self.correct_one)

        self.assertEqual(response.status_code, 200)
        answer = ReadingComprehensionAnswer.objects.get(student=self.student, question=self.question_one)
        self.assertEqual(answer.selected_answer, 'Texto')
        self.assertTrue(answer.is_correct)

    def test_incorrect_comprehension_answer_is_saved(self):
        self.client.force_login(self.user)

        response = self.post_answer(self.question_one, self.incorrect_one)

        self.assertEqual(response.status_code, 200)
        answer = ReadingComprehensionAnswer.objects.get(student=self.student, question=self.question_one)
        self.assertEqual(answer.selected_answer, 'Mapa')
        self.assertFalse(answer.is_correct)

    def test_reading_completed_and_percentage_are_saved(self):
        self.client.force_login(self.user)

        self.post_answer(self.question_one, self.correct_one)
        response = self.post_answer(self.question_two, self.incorrect_two, completed=True)

        self.assertEqual(response.status_code, 200)
        progress = ReadingProgress.objects.get(student=self.student, reading=self.reading)
        self.assertTrue(progress.completed)
        self.assertIsNotNone(progress.completed_at)
        self.assertEqual(progress.comprehension_percentage, 50)

    def test_answer_update_does_not_duplicate_progress_or_answers(self):
        self.client.force_login(self.user)

        self.post_answer(self.question_one, self.incorrect_one)
        self.post_answer(self.question_one, self.correct_one)

        self.assertEqual(ReadingProgress.objects.filter(student=self.student, reading=self.reading).count(), 1)
        self.assertEqual(ReadingComprehensionAnswer.objects.filter(student=self.student, question=self.question_one).count(), 1)
        self.assertTrue(ReadingComprehensionAnswer.objects.get(student=self.student, question=self.question_one).is_correct)

    def test_student_cannot_save_progress_for_reading_from_other_grade(self):
        other_reading = Reading.objects.create(level=self.level, title='Lectura otro grado', content='Texto.', grade='2')
        other_question = ReadingQuestion.objects.create(reading=other_reading, question='¿Otra?')
        other_answer = ReadingAnswer.objects.create(question=other_question, answer='Sí', is_correct=True)
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('readings:save_comprehension_answer', args=[other_reading.pk]),
            data=json.dumps({'question_id': other_question.pk, 'answer_id': other_answer.pk, 'completed': True}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(ReadingProgress.objects.filter(student=self.student, reading=other_reading).exists())

    def test_reading_achievement_depends_on_completed_readings(self):
        achievement = Achievement.objects.create(name='Gran lector', description='Completa lecturas.', requirement_type='readings', requirement_value=1)

        evaluate_achievements(self.student)
        self.assertFalse(StudentAchievement.objects.filter(student=self.student, achievement=achievement).exists())

        ReadingProgress.objects.create(student=self.student, reading=self.reading, completed=True, comprehension_percentage=100)
        evaluate_achievements(self.student)

        self.assertTrue(StudentAchievement.objects.filter(student=self.student, achievement=achievement).exists())
