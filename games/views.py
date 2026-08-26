import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from learning.models import Subject

from .content import GAME_CHALLENGES
from .models import Game, GameAttempt, GameAttemptAnswer
from .services import ensure_games, games_for_student, get_game_progress, get_recommended_games, get_started_games, get_student_for_user


TEMPLATE_BY_TYPE = {
    Game.GameType.LETTER_HUNTER: 'games/letter_hunter.html',
    Game.GameType.BUILD_WORD: 'games/build_word.html',
    Game.GameType.LISTEN_FIND: 'games/listen_find.html',
    Game.GameType.MEMORY: 'games/memory.html',
    Game.GameType.LETTER_DETECTIVE: 'games/letter_detective.html',
    Game.GameType.READING_PATH: 'games/reading_path.html',
    Game.GameType.DYSLEXIA_QUIZ: 'games/dyslexia_quiz.html',
}


def parse_positive_int(value, default=0):
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return default


def games_index(request):
    ensure_games()
    student = get_student_for_user(request.user)
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    games_qs = Game.objects.filter(is_active=True).select_related('level', 'subject').order_by('grade', 'subject__name', 'id')
    if student is not None:
        games_qs = games_for_student(games_qs, student)
        grade = student.grade
    elif grade:
        games_qs = games_qs.filter(grade=grade)
    if subject_id:
        games_qs = games_qs.filter(subject_id=subject_id)
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
    games = Game.objects.select_related('level', 'subject').filter(is_active=True)
    student = get_student_for_user(request.user)
    games = games_for_student(games, student)
    game = get_object_or_404(games, slug=slug)
    challenges = GAME_CHALLENGES.get(slug, [])
    template = TEMPLATE_BY_TYPE.get(game.game_type, 'games/play.html')
    return render(
        request,
        template,
        {
            'game': game,
            'challenges': challenges,
        },
    )


@login_required
@require_POST
def save_attempt(request, slug):
    student = get_student_for_user(request.user)
    if not student:
        return JsonResponse({'saved': False, 'reason': 'Solo estudiantes autenticados pueden guardar progreso.'}, status=403)
    game = get_object_or_404(games_for_student(Game.objects.filter(is_active=True), student), slug=slug)

    try:
        payload = json.loads(request.body.decode('utf-8'))
    except json.JSONDecodeError:
        return JsonResponse({'saved': False, 'reason': 'Datos invalidos.'}, status=400)

    total_questions = parse_positive_int(payload.get('total_questions'))
    correct_answers = min(parse_positive_int(payload.get('correct_answers')), total_questions)
    score = round((correct_answers / total_questions) * 100) if total_questions else 0
    attempt = GameAttempt.objects.create(
        student=student,
        game=game,
        score=score,
        correct_answers=correct_answers,
        total_questions=total_questions,
        completed=bool(payload.get('completed', True)),
        completed_at=timezone.now(),
    )
    answers = payload.get('answers', [])
    answer_rows = []
    if isinstance(answers, list):
        for index, answer in enumerate(answers, start=1):
            if not isinstance(answer, dict):
                continue
            answer_rows.append(GameAttemptAnswer(
                attempt=attempt,
                subject=str(answer.get('subject') or answer.get('category') or '')[:80],
                question=str(answer.get('question') or '')[:240],
                correct_answer=str(answer.get('correct_answer') or answer.get('answer') or '')[:120],
                selected_answer=str(answer.get('selected_answer') or '')[:120],
                is_correct=bool(answer.get('is_correct') if 'is_correct' in answer else answer.get('correct')),
                attempts_used=max(parse_positive_int(answer.get('attempts_used') or answer.get('tries'), 1), 1),
                order=index,
            ))
    if answer_rows:
        GameAttemptAnswer.objects.bulk_create(answer_rows)
    return JsonResponse({'saved': True, 'score': score})
