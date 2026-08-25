from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from learning.models import Level, Subject
from progress.services import register_attempt

from .models import Activity, ActivityOption
from .services import get_recommended_activities


def activity_list(request):
    level_id = request.GET.get('level')
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    activities = Activity.objects.filter(is_active=True).select_related('level', 'subject').order_by('subject__name', 'grade', 'level__order')
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
        'selected_level_id': level_id,
        'selected_subject_id': subject_id,
        'selected_grade': grade,
    })


def activity_detail(request, pk):
    activity = get_object_or_404(Activity.objects.prefetch_related('options'), pk=pk, is_active=True)
    return render(request, 'activities/detail.html', {'activity': activity})


@login_required
@require_POST
def submit_answer(request, pk):
    if not hasattr(request.user, 'student_profile'):
        messages.info(request, 'Solo los estudiantes pueden registrar respuestas de actividades.')
        return redirect('activities:detail', pk=pk)

    activity = get_object_or_404(Activity, pk=pk, is_active=True)
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
    else:
        messages.info(request, 'Buen intento. Puedes probar otra vez.')
    return redirect('activities:detail', pk=pk)


@login_required
def recommended(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.info(request, 'Las recomendaciones están disponibles para estudiantes.')
        return redirect('dashboard:redirect')
    activities = get_recommended_activities(student)
    return render(request, 'activities/recommended.html', {'activities': activities})
