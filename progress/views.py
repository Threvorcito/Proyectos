from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def progress_overview(request):
    student = request.user.student_profile
    return render(request, 'progress/overview.html', {'student': student})
