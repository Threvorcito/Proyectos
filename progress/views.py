from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render


@login_required
def progress_overview(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.info(request, 'El progreso está disponible para estudiantes.')
        return redirect('accounts:profile')
    return render(request, 'progress/overview.html', {'student': student})
