from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Estudiante'
        TEACHER = 'TEACHER', 'Docente'
        PARENT = 'PARENT', 'Padre o tutor'
        ADMIN = 'ADMIN', 'Administrador'

    class Gender(models.TextChoices):
        NOT_SPECIFIED = 'not_specified', 'Prefiero no decirlo'
        FEMALE = 'female', 'Femenino'
        MALE = 'male', 'Masculino'
        OTHER = 'other', 'Otro'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    email = models.EmailField(unique=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.NOT_SPECIFIED)
    profile_photo = models.ImageField(upload_to='profile-photos/', blank=True, null=True)

    def __str__(self):
        return self.get_full_name() or self.username


class LoginAttempt(models.Model):
    """Failed sign-in counter per target (account, student or client).

    Stored in the database so the limit holds across worker processes and
    cannot be reset by discarding the session cookie.
    """

    key = models.CharField(max_length=255, unique=True)
    failures = models.PositiveIntegerField(default=0)
    window_started_at = models.DateTimeField(blank=True, null=True)
    locked_until = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.key
