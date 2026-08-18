from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import CustomUser
from learning.models import Level, StudentProfile
from progress.services import register_attempt

from .models import Activity
from .services import get_recommended_activities


def activity_list(request):
    level_id = request.GET.get('level')
    activities = Activity.objects.filter(is_active=True).select_related('level')
    if level_id:
        activities = activities.filter(level_id=level_id)
    levels = Level.objects.filter(is_active=True).order_by('order')
    return render(request, 'activities/list.html', {'activities': activities, 'levels': levels})


def activity_detail(request, pk):
    activity = get_object_or_404(Activity.objects.prefetch_related('options'), pk=pk, is_active=True)
    return render(request, 'activities/detail.html', {'activity': activity})


@login_required
@require_POST
def submit_answer(request, pk):
    activity = get_object_or_404(Activity, pk=pk)
    answer = request.POST.get('answer', '')
    is_correct = request.POST.get('is_correct') == '1'
    register_attempt(request.user, activity, answer=answer, is_correct=is_correct)
    return redirect('activities:detail', pk=pk)


@login_required
def recommended(request):
    student = request.user.student_profile
    activities = get_recommended_activities(student)
    return render(request, 'activities/recommended.html', {'activities': activities})
