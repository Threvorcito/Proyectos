import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from learning.models import Subject

from .content import GAME_CHALLENGES
from .models import Game, GameAttempt
from .services import ensure_games, get_game_progress, get_recommended_games, get_started_games, get_student_for_user


TEMPLATE_BY_TYPE = {
    Game.GameType.LETTER_HUNTER: 'games/letter_hunter.html',
    Game.GameType.BUILD_WORD: 'games/build_word.html',
    Game.GameType.LISTEN_FIND: 'games/listen_find.html',
    Game.GameType.MEMORY: 'games/memory.html',
    Game.GameType.LETTER_DETECTIVE: 'games/letter_detective.html',
    Game.GameType.READING_PATH: 'games/reading_path.html',
}


def games_index(request):
    ensure_games()
    student = get_student_for_user(request.user)
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    games_qs = Game.objects.filter(is_active=True).select_related('level', 'subject').order_by('grade', 'subject__name', 'id')
    if subject_id:
        games_qs = games_qs.filter(subject_id=subject_id)
    if grade:
        games_qs = games_qs.filter(grade=grade)
    games = list(games_qs)
    progress = get_game_progress(student, games)
    game_cards = [{'game': game, 'progress': progress.get(game.id)} for game in games]
    recommended = get_recommended_games(student)
    started_games = get_started_games(student)
    return render(
        request,
        'games/index.html',
        {
            'games': games,
            'game_cards': game_cards,
            'progress': progress,
            'recommended_games': recommended,
            'started_games': started_games,
            'subjects': Subject.objects.filter(is_active=True).order_by('name'),
            'grades': [('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')],
            'selected_subject_id': subject_id,
            'selected_grade': grade,
        },
    )


def game_detail(request, slug):
    ensure_games()
    game = get_object_or_404(Game.objects.select_related('level', 'subject'), slug=slug, is_active=True)
    challenges = GAME_CHALLENGES.get(slug, [])
    template = TEMPLATE_BY_TYPE.get(game.game_type, 'games/play.html')
    return render(
        request,
        template,
        {
            'game': game,
            'challenges': challenges,
            'challenges_json': json.dumps(challenges, ensure_ascii=False),
        },
    )


@login_required
@require_POST
def save_attempt(request, slug):
    game = get_object_or_404(Game, slug=slug, is_active=True)
    student = get_student_for_user(request.user)
    if not student:
        return JsonResponse({'saved': False, 'reason': 'Solo estudiantes autenticados pueden guardar progreso.'}, status=403)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'saved': False, 'reason': 'Datos invalidos.'}, status=400)

    total_questions = max(int(payload.get('total_questions', 0)), 0)
    correct_answers = max(int(payload.get('correct_answers', 0)), 0)
    score = round((correct_answers / total_questions) * 100) if total_questions else 0
    GameAttempt.objects.create(
        student=student,
        game=game,
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions,
        completed=bool(payload.get('completed', True)),
        completed_at=timezone.now(),
    )
    return JsonResponse({'saved': True, 'score': score})
