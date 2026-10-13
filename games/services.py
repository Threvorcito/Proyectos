from django.db.models import Count, Max, Q
from unicodedata import combining, normalize

from learning.models import Level, Subject
from progress.models import StudentDifficulty

from .content import GAME_DEFINITIONS
from .models import Game, GameAttempt


def normalize_subject_name(name):
    cleaned = normalize('NFKD', name or '')
    return ''.join(character for character in cleaned if not combining(character)).lower()


def ensure_games():
    """Create built-in games that are missing; never overwrite existing rows.

    When every built-in game already exists this costs a single read query, so
    views can call it on each request without writing or undoing admin edits.
    """
    expected_slugs = {definition['slug'] for definition in GAME_DEFINITIONS}
    existing_slugs = set(Game.objects.filter(slug__in=expected_slugs).values_list('slug', flat=True))
    if existing_slugs >= expected_slugs:
        return
    levels = {level.number: level for level in Level.objects.all()}
    subjects = {normalize_subject_name(subject.name): subject for subject in Subject.objects.all()}
    language_subject = subjects.get('lengua y literatura')
    for definition in GAME_DEFINITIONS:
        if definition['slug'] in existing_slugs:
            continue
        data = definition.copy()
        level_number = data.pop('level_number')
        subject_name = data.pop('subject_name', 'Lengua y Literatura')
        subject = subjects.get(normalize_subject_name(subject_name), language_subject)
        grade = data.pop('grade', str(min(level_number, 3)))
        Game.objects.get_or_create(
            slug=data['slug'],
            defaults={**data, 'level': levels.get(level_number), 'subject': subject, 'grade': grade},
        )


def student_game_grade_filter(student):
    return Q(grade='') | Q(grade=student.grade)


def games_for_student(queryset, student):
    if student is None:
        return queryset
    return queryset.filter(student_game_grade_filter(student))


def get_student_for_user(user):
    if user.is_authenticated and hasattr(user, 'student_profile'):
        return user.student_profile
    return None


def get_recommended_games(student):
    if not student:
        games = {game.slug: game for game in Game.objects.filter(is_active=True)}
        return [games[slug] for slug in ('cazador-de-letras', 'memoria-de-palabras', 'construye-la-palabra') if slug in games]

    games = {game.slug: game for game in games_for_student(Game.objects.filter(is_active=True), student)}

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
    return games_for_student(Game.objects.filter(attempts__student=student, attempts__completed=False, is_active=True), student).distinct()[:3]
