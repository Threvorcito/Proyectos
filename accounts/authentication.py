from django.contrib.auth.backends import ModelBackend
from django.db import IntegrityError, transaction

from learning.models import TeacherProfile

from .models import CustomUser


class EmailOrTeacherBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        identifier = (username or kwargs.get(CustomUser.USERNAME_FIELD) or '').strip()
        if not identifier or not password:
            return None

        user = self._authenticate_user(identifier, password)
        if user is not None:
            return user

        teacher = TeacherProfile.objects.select_related('user').filter(email__iexact=identifier).first()
        if teacher is None or not teacher.check_password(password):
            return None

        return self._get_or_create_teacher_user(teacher)

    def _authenticate_user(self, identifier, password):
        user = CustomUser.objects.filter(email__iexact=identifier).first()
        if user is None:
            user = CustomUser.objects.filter(username__iexact=identifier).first()
        if user is not None and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def _get_or_create_teacher_user(self, teacher):
        if teacher.user_id:
            user = teacher.user
        else:
            user = CustomUser.objects.filter(email__iexact=teacher.email, role=CustomUser.Role.TEACHER).first()
            if user is None:
                try:
                    with transaction.atomic():
                        user = CustomUser.objects.create_user(
                            username=self._teacher_username(teacher),
                            email=teacher.email,
                            password=None,
                            first_name=teacher.first_name,
                            last_name=teacher.last_name,
                            role=CustomUser.Role.TEACHER,
                        )
                except IntegrityError:
                    return None
            teacher.user = user
            teacher.save(update_fields=['user'])

        user.role = CustomUser.Role.TEACHER
        user.email = teacher.email
        user.first_name = teacher.first_name
        user.last_name = teacher.last_name
        user.save(update_fields=['role', 'email', 'first_name', 'last_name'])
        return user if self.user_can_authenticate(user) else None

    def _teacher_username(self, teacher):
        base = f'docente-{teacher.pk}'
        username = base
        suffix = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f'{base}-{suffix}'
            suffix += 1
        return username
