from django.conf import settings
from django.db import models

from activities.models import Activity
from learning.models import StudentProfile


class ActivityAttempt(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='attempts')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='attempts')
    answer = models.CharField(max_length=255, blank=True)
    is_correct = models.BooleanField(default=False)
    response_time = models.FloatField(default=0)
    attempt_number = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)


class StudentProgress(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='progress_items')
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, related_name='progress_items')
    completed = models.BooleanField(default=False)
    progress_percentage = models.PositiveSmallIntegerField(default=0)
    best_score = models.PositiveSmallIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_activity_date = models.DateTimeField(blank=True, null=True)


class StudentDifficulty(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='difficulties')
    difficulty_type = models.CharField(max_length=40)
    character_a = models.CharField(max_length=20, blank=True)
    character_b = models.CharField(max_length=20, blank=True)
    syllable = models.CharField(max_length=20, blank=True)
    word = models.CharField(max_length=80, blank=True)
    error_count = models.PositiveIntegerField(default=0)
    last_error_date = models.DateTimeField(auto_now=True)
