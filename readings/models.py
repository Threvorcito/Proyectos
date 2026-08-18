from django.db import models

from learning.models import Level


class Reading(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='readings/', blank=True, null=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='readings')
    difficulty = models.CharField(max_length=20, default='easy')
    estimated_time = models.PositiveSmallIntegerField(default=3)
    audio_optional = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class ReadingQuestion(models.Model):
    class QuestionType(models.TextChoices):
        MULTIPLE_CHOICE = 'multiple_choice', 'Opción múltiple'
        TRUE_FALSE = 'true_false', 'Verdadero o falso'

    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='questions')
    question = models.CharField(max_length=255)
    question_type = models.CharField(max_length=30, choices=QuestionType.choices, default=QuestionType.MULTIPLE_CHOICE)

    def __str__(self):
        return self.question


class ReadingAnswer(models.Model):
    question = models.ForeignKey(ReadingQuestion, on_delete=models.CASCADE, related_name='answers')
    answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.answer
