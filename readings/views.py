from django.shortcuts import get_object_or_404, render

from learning.models import Subject

from .models import Reading


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
        'selected_subject_id': subject_id,
        'selected_grade': grade,
    })


def reading_detail(request, pk):
    readings = Reading.objects.select_related('subject', 'level').prefetch_related('questions__answers').filter(is_active=True)
    student = getattr(request.user, 'student_profile', None)
    if student is not None:
        readings = readings.filter(grade=student.grade)
    reading = get_object_or_404(readings, pk=pk)
    return render(request, 'readings/detail.html', {'reading': reading})
