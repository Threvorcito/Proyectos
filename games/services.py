from django.db.models import Count, Max
from unicodedata import combining, normalize

from learning.models import Level, Subject
from progress.models import StudentDifficulty

from .content import GAME_DEFINITIONS
from .models import Game, GameAttempt


def normalize_subject_name(name):
    cleaned = normalize('NFKD', name or '')
    return ''.join(character for character in cleaned if not combining(character)).lower()


def ensure_games():
    levels = {level.number: level for level in Level.objects.all()}
    subjects = {normalize_subject_name(subject.name): subject for subject in Subject.objects.all()}
    language_subject = subjects.get('lengua y literatura')
    games = []
    for definition in GAME_DEFINITIONS:
        data = definition.copy()
        level_number = data.pop('level_number')
        subject_name = data.pop('subject_name', 'Lengua y Literatura')
        subject = subjects.get(normalize_subject_name(subject_name), language_subject)
        game, _ = Game.objects.update_or_create(
            slug=data['slug'],
            defaults={**data, 'level': levels.get(level_number), 'subject': subject, 'grade': str(min(level_number, 3))},
        )
        games.append(game)
    return games


def get_student_for_user(user):
    if user.is_authenticated and hasattr(user, 'student_profile'):
        return user.student_profile
    return None


def get_recommended_games(student):
    ensure_games()
    games = {game.slug: game for game in Game.objects.filter(is_active=True)}
    if not student:
        return [games[slug] for slug in ('cazador-de-letras', 'memoria-de-palabras', 'construye-la-palabra') if slug in games]

    difficulty = StudentDifficulty.objects.filter(student=student).order_by('-error_count', '-last_error_date').first()
    if difficulty:
        pair = f'{difficulty.character_a}/{difficulty.character_b}'.lower()
        if pair in ('b/d', 'd/b', 'p/q', 'q/p', 'm/n', 'n/m'):
            return [games[slug] for slug in ('detective-de-letras', 'cazador-de-letras') if slug in games]
        if difficulty.syllable:
            return [games[slug] for slug in ('construye-la-palabra', 'camino-de-lectura') if slug in games]
        if difficulty.difficulty_type.lower() in ('audio', 'sonido', 'fonologica', 'phonological_awareness'):
            return [games[slug] for slug in ('escucha-y-encuentra', 'memoria-de-palabras') if slug in games]

    current_level = student.current_level or student.reading_level
    level_number = current_level.number if current_level else 1
    if level_number <= 1:
        slugs = ('cazador-de-letras', 'memoria-de-palabras', 'construye-la-palabra')
    elif level_number == 2:
        slugs = ('quiz-agilidad-lectora', 'escucha-y-encuentra', 'detective-de-letras')
    else:
        slugs = ('camino-de-lectura', 'quiz-agilidad-lectora', 'escucha-y-encuentra')
    return [games[slug] for slug in slugs if slug in games]


def get_game_progress(student, games):
    if not student:
        return {}
    attempts = (
        GameAttempt.objects.filter(student=student, game__in=games)
        .values('game_id')
        .annotate(attempt_count=Count('id'), best_score=Max('score'))
    )
    return {item['game_id']: item for item in attempts}


def get_started_games(student):
    if not student:
        return []
    return Game.objects.filter(attempts__student=student, attempts__completed=False, is_active=True).distinct()[:3]
