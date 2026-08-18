from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from activities.services import get_recommended_activities
from gamification.services import evaluate_achievements
from learning.models import StudentProfile


def is_teacher(user):
    return user.is_authenticated and user.role == 'TEACHER'


def is_parent(user):
    return user.is_authenticated and user.role == 'PARENT'


@login_required
def redirect_after_login(request):
    role = getattr(request.user, 'role', 'STUDENT')
    if role == 'TEACHER':
        return redirect('dashboard:teacher')
    if role == 'PARENT':
        return redirect('dashboard:parents')
    return redirect('dashboard:student')


@login_required
def student_dashboard(request):
    student = request.user.student_profile
    evaluate_achievements(student)
    recommended = get_recommended_activities(student)
    return render(request, 'dashboard/student_dashboard.html', {'student': student, 'recommended': recommended})


@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    students = StudentProfile.objects.select_related('user', 'current_level').all().order_by('name')
    return render(request, 'dashboard/teacher_dashboard.html', {'students': students})


@login_required
@user_passes_test(is_parent)
def parent_dashboard(request):
    return render(request, 'dashboard/parent_dashboard.html', {'parent': request.user.parent_profile})
