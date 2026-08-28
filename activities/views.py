from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from learning.models import Level, Subject
from progress.services import register_attempt

from .models import Activity, ActivityOption
from .services import get_recommended_activities


def activity_list(request):
    level_id = request.GET.get('level')
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    student = getattr(request.user, 'student_profile', None)
    activities = Activity.objects.filter(is_active=True).select_related('level', 'subject').order_by('subject__name', 'grade', 'level__order')
    if student is not None:
        activities = activities.filter(grade=student.grade)
        grade = student.grade
    if level_id:
        activities = activities.filter(level_id=level_id)
    if subject_id:
        activities = activities.filter(subject_id=subject_id)
    if grade:
        activities = activities.filter(grade=grade)
    levels = Level.objects.filter(is_active=True).order_by('order')
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    grades = [('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')]
    return render(request, 'activities/list.html', {
        'activities': activities,
        'levels': levels,
        'subjects': subjects,
        'grades': grades,
        'student': student,
        'selected_level_id': level_id,
        'selected_subject_id': subject_id,
        'selected_grade': grade,
    })


def activity_detail(request, pk):
    activities = Activity.objects.prefetch_related('options').filter(is_active=True)
    student = getattr(request.user, 'student_profile', None)
    if student is not None:
        activities = activities.filter(grade=student.grade)
    activity = get_object_or_404(activities, pk=pk)
    selected_option = None
    result = request.GET.get('resultado')
    option_id = request.GET.get('opcion')
    if option_id:
        selected_option = activity.options.filter(pk=option_id).first()
    answer_feedback = None
    if selected_option and result in ('correcta', 'intenta'):
        answer_feedback = {
            'option': selected_option,
            'is_correct': result == 'correcta',
            'points': activity.points if result == 'correcta' else 0,
            'stars': activity.stars if result == 'correcta' else 0,
        }
    return render(request, 'activities/detail.html', {'activity': activity, 'answer_feedback': answer_feedback})


@login_required
@require_POST
def submit_answer(request, pk):
    if not hasattr(request.user, 'student_profile'):
        messages.info(request, 'Solo los estudiantes pueden registrar respuestas de actividades.')
        return redirect('activities:detail', pk=pk)

    student = request.user.student_profile
    activity = get_object_or_404(Activity, pk=pk, is_active=True, grade=student.grade)
    option = get_object_or_404(ActivityOption, pk=request.POST.get('option_id'), activity=activity)
    answer = option.text
    is_correct = option.is_correct
    correct_option = activity.options.filter(is_correct=True).order_by('order', 'pk').first()
    register_attempt(
        request.user,
        activity,
        answer=answer,
        is_correct=is_correct,
        correct_answer=correct_option.text if correct_option else '',
    )
    if is_correct:
        messages.success(request, 'Respuesta correcta. Ganaste puntos por tu esfuerzo.')
        result = 'correcta'
    else:
        messages.info(request, 'Buen intento. Puedes probar otra vez.')
        result = 'intenta'
    return redirect(f"{reverse('activities:detail', args=[pk])}?opcion={option.pk}&resultado={result}")


@login_required
def recommended(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.info(request, 'Las recomendaciones están disponibles para estudiantes.')
        return redirect('dashboard:redirect')
    activities = get_recommended_activities(student)
    return render(request, 'activities/recommended.html', {'activities': activities})
