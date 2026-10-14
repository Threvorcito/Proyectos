"""Database-backed lockout for repeated failed sign-ins.

Policy: MAX_FAILURES failures inside WINDOW lock the key for LOCK_DURATION.
A successful sign-in resets the key.

Progressive lock (opt-in per call, used for the child visual key): ESCALATE_AFTER
lockouts inside ESCALATE_WINDOW keep the key locked until an adult unlocks it.
A longer failure `window` stops slow guessing that never reaches a lock.
"""
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from .models import CustomUser, LoginAttempt

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)
LOCK_DURATION = timedelta(minutes=15)
ESCALATE_AFTER = 3
ESCALATE_WINDOW = timedelta(hours=24)


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
    return LoginAttempt.objects.filter(key=key).filter(
        Q(locked_until__gt=_now()) | Q(requires_unlock=True),
    ).exists()


def needs_unlock(key):
    return bool(key) and LoginAttempt.objects.filter(key=key, requires_unlock=True).exists()


def locked_keys(keys):
    """Return the subset of keys that are currently locked (one query)."""
    return set(
        LoginAttempt.objects.filter(key__in=list(keys)).filter(
            Q(locked_until__gt=_now()) | Q(requires_unlock=True),
        ).values_list('key', flat=True)
    )


def register_failure(key, max_failures=MAX_FAILURES, escalate_after=None, window=WINDOW):
    if not key:
        return
    now = _now()
    with transaction.atomic():
        attempt, _ = LoginAttempt.objects.select_for_update().get_or_create(key=key)
        if attempt.window_started_at is None or now - attempt.window_started_at > window:
            attempt.failures = 0
            attempt.window_started_at = now
        attempt.failures += 1
        if attempt.failures >= max_failures:
            attempt.locked_until = now + LOCK_DURATION
            attempt.failures = 0
            attempt.window_started_at = None
            if escalate_after:
                if attempt.lockouts_started_at is None or now - attempt.lockouts_started_at > ESCALATE_WINDOW:
                    attempt.lockouts = 0
                    attempt.lockouts_started_at = now
                attempt.lockouts += 1
                if attempt.lockouts >= escalate_after:
                    attempt.requires_unlock = True
        attempt.save()


def reset(key):
    """Clear every counter for the key (successful sign-in or an adult unlock)."""
    if key:
        LoginAttempt.objects.filter(key=key).delete()
