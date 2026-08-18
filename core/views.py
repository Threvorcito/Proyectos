from django.shortcuts import redirect, render


def home(request):
    return render(request, 'core/home.html')


def privacy(request):
    return render(request, 'core/simple_page.html', {'title': 'Privacidad'})
