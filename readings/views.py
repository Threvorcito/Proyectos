import math

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from core.json_payload import parse_id, parse_json_object
from learning.models import Subject
from progress.services import complete_reading_practice

from .models import (
    Reading,
    ReadingAnswer,
    ReadingComprehensionAnswer,
    ReadingPracticeAttempt,
    ReadingPracticeSession,
    ReadingProgress,
    ReadingQuestion,
)
from .services import (
    MAX_READ_MS,
    MAX_WORDS_PER_MINUTE,
    MIN_READ_MS,
    PRACTICE_READS,
    count_words,
    practice_history,
    words_per_minute,
)


def reading_list(request):
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    student = getattr(request.user, 'student_profile', None)
    readings = Reading.objects.filter(is_active=True).select_related('level', 'subject').order_by('grade', 'subject__name')
    if student is not None:
        readings = readings.filter(grade=student.grade)
        grade = student.grade
    if subject_id:
        readings = readings.filter(subject_id=subject_id)
    if grade:
        readings = readings.filter(grade=grade)
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    return render(request, 'readings/list.html', {
        'readings': readings,
        'subjects': subjects,
        'grades': [('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')],
        'student': student,
        'selected_subject_id': subject_id,
        'selected_grade': grade,
    })


@ensure_csrf_cookie
def reading_detail(request, pk):
    readings = Reading.objects.select_related('subject', 'level').prefetch_related('questions__answers').filter(is_active=True)
    student = getattr(request.user, 'student_profile', None)
    if student is not None:
        readings = readings.filter(grade=student.grade)
    reading = get_object_or_404(readings, pk=pk)
    if student is not None:
        ReadingProgress.objects.get_or_create(student=student, reading=reading)
    return render(request, 'readings/detail.html', {
        'reading': reading,
        'student': student,
        'practice_reads': PRACTICE_READS,
        'practice_min_ms': MIN_READ_MS,
        'practice_max_ms': MAX_READ_MS,
    })


def calculate_comprehension_percentage(student, reading):
    total_questions = ReadingQuestion.objects.filter(reading=reading).count()
    if not total_questions:
        return 0
    correct_answers = ReadingComprehensionAnswer.objects.filter(student=student, reading=reading, is_correct=True).count()
    return round((correct_answers / total_questions) * 100)


@login_required
@require_POST
def save_comprehension_answer(request, pk):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        return JsonResponse({'saved': False, 'reason': 'Solo estudiantes pueden guardar comprensión.'}, status=403)
    reading = get_object_or_404(Reading.objects.filter(is_active=True, grade=student.grade), pk=pk)
    payload = parse_json_object(request)
    question_id = parse_id(payload.get('question_id')) if payload is not None else None
    answer_id = parse_id(payload.get('answer_id')) if payload is not None else None
    if question_id is None or answer_id is None:
        return JsonResponse({'saved': False, 'reason': 'Datos invalidos.'}, status=400)

    question = get_object_or_404(ReadingQuestion, pk=question_id, reading=reading)
    answer = get_object_or_404(ReadingAnswer, pk=answer_id, question=question)
    ReadingComprehensionAnswer.objects.update_or_create(
        student=student,
        question=question,
        defaults={
            'reading': reading,
            'selected_answer': answer.answer,
            'is_correct': answer.is_correct,
        },
    )
    progress, _ = ReadingProgress.objects.get_or_create(student=student, reading=reading)
    progress.comprehension_percentage = calculate_comprehension_percentage(student, reading)
    if payload.get('completed'):
        progress.completed = True
        progress.completed_at = timezone.now()
    progress.save(update_fields=['comprehension_percentage', 'completed', 'completed_at'])
    return JsonResponse({
        'saved': True,
        'is_correct': answer.is_correct,
        'comprehension_percentage': progress.comprehension_percentage,
        'completed': progress.completed,
    })


def _parse_duration_ms(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return int(round(value))


def _practice_error(reason, status=400):
    return JsonResponse({'saved': False, 'reason': reason}, status=status)


@login_required
@require_POST
def save_practice_attempt(request, pk):
    """Save one timed read of the practice cycle; the third read closes the cycle."""
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        return _practice_error('student_only', status=403)
    reading = get_object_or_404(Reading.objects.filter(is_active=True, grade=student.grade), pk=pk)
    payload = parse_json_object(request)
    if payload is None:
        return _practice_error('payload')
    attempt_number = parse_id(payload.get('attempt_number'))
    duration_ms = _parse_duration_ms(payload.get('duration_ms'))
    if attempt_number is None or attempt_number > PRACTICE_READS or duration_ms is None:
        return _practice_error('payload')
    if not MIN_READ_MS <= duration_ms <= MAX_READ_MS:
        return _practice_error('duration')
    word_count = count_words(reading.content)
    wpm = words_per_minute(word_count, duration_ms)
    if word_count == 0 or wpm > MAX_WORDS_PER_MINUTE:
        return _practice_error('duration')

    with transaction.atomic():
        if attempt_number == 1:
            session = ReadingPracticeSession.objects.create(student=student, reading=reading)
        else:
            session_id = parse_id(payload.get('session_id'))
            session = (
                ReadingPracticeSession.objects.select_for_update()
                .filter(pk=session_id, student=student, reading=reading, completed_at__isnull=True)
                .first()
            ) if session_id else None
            if session is None or session.attempts.count() != attempt_number - 1:
                return _practice_error('session')
        ReadingPracticeAttempt.objects.create(
            session=session,
            attempt_number=attempt_number,
            duration_ms=duration_ms,
            word_count=word_count,
            words_per_minute=wpm,
        )
        points = stars = 0
        completed = attempt_number == PRACTICE_READS
        if completed:
            points, stars = complete_reading_practice(session)

    response = {
        'saved': True,
        'session_id': session.pk,
        'attempt_number': attempt_number,
        'word_count': word_count,
        'words_per_minute': wpm,
        'completed': completed,
    }
    if completed:
        response.update({
            'points_awarded': points,
            'stars_awarded': stars,
            'attempts': [
                {'attempt_number': item.attempt_number, 'words_per_minute': item.words_per_minute}
                for item in session.attempts.all()
            ],
            'history': practice_history(student, reading, exclude_session_id=session.pk),
        })
    return JsonResponse(response)
