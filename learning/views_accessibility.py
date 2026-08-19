from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, render

from .forms import AccessibilityPreferenceForm
from .models import AccessibilityPreference


@login_required
def accessibility_settings(request):
    student = getattr(request.user, 'student_profile', None)
    if student is None:
        messages.info(request, 'Las preferencias de lectura están disponibles para estudiantes.')
        return redirect('dashboard:redirect')

    preference, _ = AccessibilityPreference.objects.get_or_create(student=student)
    if request.method == 'POST':
        form = AccessibilityPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            return redirect('dashboard:student')
    else:
        form = AccessibilityPreferenceForm(instance=preference)
    return render(request, 'learning/accessibility.html', {'form': form})
