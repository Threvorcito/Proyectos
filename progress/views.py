from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from games.models import GameAttempt
from readings.models import ReadingProgress
from readings.services import practice_summary

from .models import StudentProgress
from .services import practice_days

RECENT_LIMIT = 6
GROWTH_LIMIT = 4
# Inline SVG geometry for the "before / now" bars (viewBox 0 0 220 150).
BAR_BASELINE = 112
BAR_MAX_HEIGHT = 92
BAR_MIN_HEIGHT = 8

GROWTH_MESSAGES = {
    'up': '¡Lees más rápido que antes!',
    'steady': '¡Lees parejo y con calma!',
    'down': 'Hoy fue más despacio. ¡Está bien, sigue practicando!',
}


def _bar(value, top):
    height = max(BAR_MIN_HEIGHT, round(value / top * BAR_MAX_HEIGHT)) if top else BAR_MIN_HEIGHT
    return {'height': height, 'y': BAR_BASELINE - height}


def growth_cards(student):
    """Own-history reading growth: first read ever vs latest read, per practised text."""
    cards = []
    for row in practice_summary(student, limit=GROWTH_LIMIT):
        top = max(row['first_wpm'], row['last_wpm'])
        cards.append({
            'reading': row['reading'],
            'trend': row['trend'],
            'message': GROWTH_MESSAGES[row['trend']],
            'first_wpm': row['first_wpm'],
            'last_wpm': row['last_wpm'],
            'before': _bar(row['first_wpm'], top),
            'now': _bar(row['last_wpm'], top),
        })
    return cards


def recent_finished(student, limit=RECENT_LIMIT):
    items = []
    for progress in StudentProgress.objects.filter(student=student, completed=True).select_related('activity').order_by('-last_activity_date')[:limit]:
        items.append({'kind': 'practice', 'label': 'Actividad', 'icon': '✏️', 'title': progress.activity.title, 'when': progress.last_activity_date})
    for progress in ReadingProgress.objects.filter(student=student, completed=True).select_related('reading').order_by('-completed_at')[:limit]:
        items.append({'kind': 'read', 'label': 'Cuento', 'icon': '📖', 'title': progress.reading.title, 'when': progress.completed_at})
    for attempt in GameAttempt.objects.filter(student=student, completed=True).select_related('game').order_by('-completed_at')[:limit]:
        items.append({'kind': 'play', 'label': 'Juego', 'icon': attempt.game.icon or '🎲', 'title': attempt.game.name, 'when': attempt.completed_at or attempt.started_at})
    items.sort(key=lambda item: (item['when'] is not None, item['when']), reverse=True)
    return items[:limit]


@login_required
def progress_overview(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.info(request, 'El progreso está disponible para estudiantes.')
        return redirect('accounts:profile')
    return render(request, 'progress/overview.html', {
        'student': student,
        'practice_days': practice_days(student),
        'growth_cards': growth_cards(student),
        'recent_items': recent_finished(student),
    })
