import re

from django.db.models import Max

from .models import ReadingPracticeSession

WORD_PATTERN = re.compile(r'[^\W_]+')

PRACTICE_READS = 3
MIN_READ_MS = 2_000
MAX_READ_MS = 15 * 60 * 1000
# A child aged 6-9 cannot read faster than this; above it the tap was a slip.
MAX_WORDS_PER_MINUTE = 400


def count_words(text):
    return len(WORD_PATTERN.findall(text or ''))


def words_per_minute(word_count, duration_ms):
    return round(word_count * 60_000 / duration_ms) if duration_ms else 0


def practice_trend(first_wpm, last_wpm):
    """Return 'up', 'steady' or 'down' with a 5% dead band around equal speeds."""
    if not first_wpm:
        return 'steady'
    ratio = last_wpm / first_wpm
    if ratio > 1.05:
        return 'up'
    if ratio < 0.95:
        return 'down'
    return 'steady'


def practice_history(student, reading, exclude_session_id=None, limit=4):
    """Last-read speed of earlier finished cycles for this reading, oldest first."""
    sessions = (
        ReadingPracticeSession.objects.filter(student=student, reading=reading, completed_at__isnull=False)
        .exclude(pk=exclude_session_id)
        .prefetch_related('attempts')
        .order_by('-completed_at')[:limit]
    )
    history = []
    for session in reversed(list(sessions)):
        attempts = list(session.attempts.all())
        if attempts:
            history.append({'date': session.completed_at.isoformat(), 'words_per_minute': attempts[-1].words_per_minute})
    return history


def practice_summary(student, limit=10):
    """Per-reading summary of finished practice cycles for the teacher report.

    First speed is the first read of the earliest cycle; last speed is the final
    read of the latest cycle, so the trend shows growth on that text over time.
    """
    latest = list(
        ReadingPracticeSession.objects.filter(student=student, completed_at__isnull=False)
        .values('reading_id')
        .annotate(last_completed=Max('completed_at'))
        .order_by('-last_completed')[:limit]
    )
    reading_ids = [row['reading_id'] for row in latest]
    sessions = (
        ReadingPracticeSession.objects.filter(student=student, reading_id__in=reading_ids, completed_at__isnull=False)
        .select_related('reading')
        .prefetch_related('attempts')
        .order_by('completed_at')
    )
    grouped = {}
    for session in sessions:
        attempts = list(session.attempts.all())
        if not attempts:
            continue
        row = grouped.setdefault(session.reading_id, {
            'reading': session.reading,
            'sessions': 0,
            'first_wpm': attempts[0].words_per_minute,
        })
        row['sessions'] += 1
        row['last_date'] = session.completed_at
        row['last_wpm'] = attempts[-1].words_per_minute
    rows = [grouped[reading_id] for reading_id in reading_ids if reading_id in grouped]
    for row in rows:
        row['trend'] = practice_trend(row['first_wpm'], row['last_wpm'])
    return rows
