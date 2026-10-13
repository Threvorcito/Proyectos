from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST

from core.json_payload import parse_id, parse_json_object
from learning.models import Subject

from .models import Reading, ReadingAnswer, ReadingComprehensionAnswer, ReadingProgress, ReadingQuestion


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
    return render(request, 'readings/detail.html', {'reading': reading, 'student': student})


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
