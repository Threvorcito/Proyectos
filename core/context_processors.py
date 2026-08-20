def site_context(request):
    accessibility_preference = None
    user = getattr(request, 'user', None)
    student = getattr(user, 'student_profile', None) if getattr(user, 'is_authenticated', False) else None
    if student is not None:
        accessibility_preference = getattr(student, 'accessibility', None)

    return {
        'site_name': 'Lectura sin Límites',
        'site_tagline': 'Cada palabra es un nuevo comienzo.',
        'accessibility_preference': accessibility_preference,
    }
