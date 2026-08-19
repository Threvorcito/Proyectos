from django.shortcuts import get_object_or_404, render

from learning.models import Subject

from .models import Reading


def reading_list(request):
    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    readings = Reading.objects.filter(is_active=True).select_related('level', 'subject').order_by('grade', 'subject__name')
    if subject_id:
        readings = readings.filter(subject_id=subject_id)
    if grade:
        readings = readings.filter(grade=grade)
    subjects = Subject.objects.filter(is_active=True).order_by('name')
    return render(request, 'readings/list.html', {
        'readings': readings,
        'subjects': subjects,
        'grades': [('1', 'Primer grado'), ('2', 'Segundo grado'), ('3', 'Tercer grado')],
        'selected_subject_id': subject_id,
        'selected_grade': grade,
    })


def reading_detail(request, pk):
    reading = get_object_or_404(Reading.objects.select_related('subject', 'level').prefetch_related('questions__answers'), pk=pk, is_active=True)
    return render(request, 'readings/detail.html', {'reading': reading})
