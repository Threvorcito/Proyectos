"""Database-backed lockout for repeated failed sign-ins.

Policy: MAX_FAILURES failures inside WINDOW lock the key for LOCK_DURATION.
A successful sign-in resets the key.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import CustomUser, LoginAttempt

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK_DURATION = timedelta(minutes=15)


def _now():
    return timezone.now()


def student_key(student_id):
    return f'student:{student_id}'


def password_login_key(identifier):
    """Key a username/email login by the account it resolves to.

    Username and email of the same account share one counter, so switching
    between them (or their letter case) does not reset the limit.
    """
    identifier = (identifier or '').strip()
    if not identifier:
        return None
    user_id = (
        CustomUser.objects.filter(email__iexact=identifier).values_list('pk', flat=True).first()
        or CustomUser.objects.filter(username__iexact=identifier).values_list('pk', flat=True).first()
    )
    if user_id:
        return f'user:{user_id}'
    return f'login:{identifier.lower()[:200]}'


def is_locked(key):
    if not key:
        return False
    return LoginAttempt.objects.filter(key=key, locked_until__gt=_now()).exists()


def register_failure(key, max_failures=MAX_FAILURES):
    if not key:
        return
    now = _now()
    with transaction.atomic():
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(key=key)
        if attempt.window_started_at is None or now - attempt.window_started_at > WINDOW:
            attempt.failures = 0
            attempt.window_started_at = now
        attempt.failures += 1
        if attempt.failures >= max_failures:
            attempt.locked_until = now + LOCK_DURATION
            attempt.failures = 0
            attempt.window_started_at = None
        attempt.save()


def reset(key):
    if key:
        LoginAttempt.objects.filter(key=key).delete()
