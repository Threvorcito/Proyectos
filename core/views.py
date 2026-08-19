from django.shortcuts import redirect, render


def home(request):
    return render(request, 'core/home.html')


def privacy(request):
    return render(request, 'core/simple_page.html', {'title': 'Privacidad'})


def page_not_found(request, exception=None):
    return render(request, '404.html', status=404)


def error_preview(request):
    return page_not_found(request)
