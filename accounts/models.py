from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = 'STUDENT', 'Estudiante'
        TEACHER = 'TEACHER', 'Docente'
        PARENT = 'PARENT', 'Padre o tutor'
        ADMIN = 'ADMIN', 'Administrador'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.get_full_name() or self.username
