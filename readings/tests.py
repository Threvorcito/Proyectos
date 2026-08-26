from django.test import TestCase
from django.urls import reverse

from accounts.models import CustomUser
from learning.models import Level, StudentProfile

from .models import Reading


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
            for other_grade in {'1', '2', '3'} - {grade}:
                self.assertNotContains(response, f'Lectura grado {other_grade}')

    def test_student_cannot_open_reading_from_other_grade(self):
        self.client.force_login(self.students['1'].user)
        other_reading = Reading.objects.get(title='Lectura grado 2')

        response = self.client.get(reverse('readings:detail', args=[other_reading.pk]))

        self.assertEqual(response.status_code, 404)
