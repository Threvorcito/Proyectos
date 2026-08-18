from django.db import models

from learning.models import StudentProfile


class Achievement(models.Model):
    name = models.CharField(max_length=160)
    description = models.TextField()
    icon = models.CharField(max_length=10, default='⭐')
    requirement_type = models.CharField(max_length=40)
    requirement_value = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name


class StudentAchievement(models.Model):
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)
