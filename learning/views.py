from django.shortcuts import render

from .models import Level


def level_list(request):
    levels = Level.objects.filter(is_active=True).order_by('order', 'number')
    return render(request, 'learning/levels.html', {'levels': levels})
