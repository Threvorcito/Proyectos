from django.db import models
from django.utils import timezone

from learning.models import CurriculumCompetency, Level, StudentProfile, Subject


GAME_GRADE_CHOICES = [('', 'General')] + list(StudentProfile.Grade.choices)


class Game(models.Model):
    class GameType(models.TextChoices):
        LETTER_HUNTER = 'letter_hunter', 'Cazador de letras'
        BUILD_WORD = 'build_word', 'Construye la palabra'
        LISTEN_FIND = 'listen_find', 'Escucha y encuentra'
        MEMORY = 'memory', 'Memoria de palabras'
        LETTER_DETECTIVE = 'letter_detective', 'Detective de letras'
        READING_PATH = 'reading_path', 'Camino de lectura'
        DYSLEXIA_QUIZ = 'dyslexia_quiz', 'Quiz de lectura'

    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    skill = models.CharField(max_length=120)
    game_type = models.CharField(max_length=40, choices=GameType.choices)
    level = models.ForeignKey(Level, on_delete=models.SET_NULL, null=True, blank=True, related_name='games')
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, blank=True, null=True, related_name='games')
    competency = models.ForeignKey(CurriculumCompetency, on_delete=models.SET_NULL, blank=True, null=True, related_name='games')
    grade = models.CharField(max_length=1, choices=GAME_GRADE_CHOICES, blank=True, default=StudentProfile.Grade.FIRST)
    icon = models.CharField(max_length=10, default='🎮')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class GameAttempt(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='game_attempts')
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='attempts')
    score = models.PositiveSmallIntegerField(default=0)
    correct_answers = models.PositiveSmallIntegerField(default=0)
    total_questions = models.PositiveSmallIntegerField(default=0)
    completed = models.BooleanField(default=False)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.student} - {self.game}'


class GameAttemptAnswer(models.Model):
    attempt = models.ForeignKey(GameAttempt, on_delete=models.CASCADE, related_name='answers')
    subject = models.CharField(max_length=80)
    question = models.CharField(max_length=240)
    correct_answer = models.CharField(max_length=120)
    selected_answer = models.CharField(max_length=120, blank=True)
    is_correct = models.BooleanField(default=False)
    attempts_used = models.PositiveSmallIntegerField(default=1)
    order = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.subject} - {self.correct_answer}'
