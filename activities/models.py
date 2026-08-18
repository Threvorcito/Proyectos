from django.db import models

from learning.models import Level


class Activity(models.Model):
    class ActivityType(models.TextChoices):
        LISTEN_SELECT = 'LISTEN_SELECT', 'Escucha y selecciona'
        MATCH_IMAGE_WORD = 'MATCH_IMAGE_WORD', 'Une imagen y palabra'
        FORM_WORD = 'FORM_WORD', 'Forma la palabra'
        COMPLETE_WORD = 'COMPLETE_WORD', 'Completa la palabra'
        FIND_LETTER = 'FIND_LETTER', 'Encuentra la letra'
        SIMILAR_LETTERS = 'SIMILAR_LETTERS', 'Letras parecidas'
        SYLLABLES = 'SYLLABLES', 'Sílabas'
        READING = 'READING', 'Lectura'

    level = models.ForeignKey(Level, on_delete=models.CASCADE, related_name='activities')
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    activity_type = models.CharField(max_length=30, choices=ActivityType.choices)
    difficulty = models.CharField(max_length=20, default='easy')
    points = models.PositiveIntegerField(default=10)
    stars = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class ActivityOption(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=120)
    image = models.ImageField(upload_to='activity-options/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    order = models.PositiveSmallIntegerField(default=1)

    def __str__(self):
        return self.text
