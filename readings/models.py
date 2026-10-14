from django.db import models

from learning.models import CurriculumCompetency, Level, StudentProfile, Subject


class Reading(models.Model):
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='readings/', blank=True, null=True)
    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='readings')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, blank=True, null=True, related_name='readings')
    competency = models.ForeignKey(CurriculumCompetency, on_delete=models.SET_NULL, blank=True, null=True, related_name='readings')
    grade = models.CharField(max_length=1, choices=StudentProfile.Grade.choices, default=StudentProfile.Grade.FIRST)
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


class ReadingProgress(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reading_progress')
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='student_progress')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    completed = models.BooleanField(default=False)
    comprehension_percentage = models.PositiveSmallIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'reading'], name='unique_reading_progress_per_student'),
        ]

    def __str__(self):
        return f'{self.student} - {self.reading}'


class ReadingComprehensionAnswer(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reading_answers')
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='student_answers')
    question = models.ForeignKey(ReadingQuestion, on_delete=models.CASCADE, related_name='student_answers')
    selected_answer = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'question'], name='unique_reading_answer_per_student_question'),
        ]

    def __str__(self):
        return f'{self.student} - {self.question}'


class ReadingPracticeSession(models.Model):
    """One repeated-reading cycle: listen to the model, then read the text three times."""

    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='reading_practice_sessions')
    reading = models.ForeignKey(Reading, on_delete=models.CASCADE, related_name='practice_sessions')
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    points_awarded = models.PositiveSmallIntegerField(default=0)

    class Meta:
        indexes = [models.Index(fields=['student', 'reading', 'completed_at'])]

    def __str__(self):
        return f'{self.student} - {self.reading} ({self.started_at:%Y-%m-%d})'


class ReadingPracticeAttempt(models.Model):
    """A single timed read. Words per minute are computed on the server."""

    session = models.ForeignKey(ReadingPracticeSession, on_delete=models.CASCADE, related_name='attempts')
    attempt_number = models.PositiveSmallIntegerField()
    duration_ms = models.PositiveIntegerField()
    word_count = models.PositiveIntegerField()
    words_per_minute = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['attempt_number']
        constraints = [
            models.UniqueConstraint(fields=['session', 'attempt_number'], name='unique_practice_attempt_number'),
        ]

    def __str__(self):
        return f'{self.session} #{self.attempt_number}'
