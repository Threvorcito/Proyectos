from django.shortcuts import get_object_or_404, render

from .models import Reading


def reading_list(request):
    readings = Reading.objects.filter(is_active=True).select_related('level')
    return render(request, 'readings/list.html', {'readings': readings})


def reading_detail(request, pk):
    reading = get_object_or_404(Reading.objects.prefetch_related('questions__answers'), pk=pk, is_active=True)
    return render(request, 'readings/detail.html', {'reading': reading})
