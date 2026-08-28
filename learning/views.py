from activities.models import Activity
from games.models import Game
from games.services import games_for_student
from readings.models import Reading

from django.shortcuts import get_object_or_404, render

from .models import LessonPlan, LessonPlanAssignment, Level, Subject


def level_list(request):
    levels = Level.objects.filter(is_active=True).order_by('order', 'number')
    student = getattr(request.user, 'student_profile', None)
    teacher = getattr(request.user, 'teacher_profile', None)
    level_cards = []
    for level in levels:
        grade = str(min(level.number, 3))
        resource_grade = student.grade if student else grade
        assigned_count = 0
        if student:
            assigned_count = LessonPlanAssignment.objects.filter(student=student, plan__level=level, is_active=True).count()
        elif teacher:
            assigned_count = LessonPlan.objects.filter(teacher=teacher, level=level, is_active=True).count()
        level_cards.append({
            'level': level,
            'grade': grade,
            'activities_count': Activity.objects.filter(is_active=True, level=level, grade=resource_grade).count(),
            'readings_count': Reading.objects.filter(is_active=True, level=level, grade=resource_grade).count(),
            'games_count': games_for_student(Game.objects.filter(is_active=True, level=level), student).count() if student else Game.objects.filter(is_active=True, level=level, grade=resource_grade).count(),
            'plans_count': assigned_count,
        })
    upcoming_plans = []
    if student:
        upcoming_plans = LessonPlanAssignment.objects.filter(student=student, is_active=True).select_related('plan', 'plan__subject', 'plan__level').order_by('-assigned_at')[:4]
    elif teacher:
        upcoming_plans = LessonPlan.objects.filter(teacher=teacher, is_active=True).select_related('subject', 'level').order_by('-created_at')[:4]
    return render(request, 'learning/levels.html', {
        'level_cards': level_cards,
        'student': student,
        'teacher': teacher,
        'upcoming_plans': upcoming_plans,
    })


def level_detail(request, number):
    level = get_object_or_404(Level, number=number, is_active=True)
    subjects = list(Subject.objects.filter(is_active=True).order_by('name'))
    student = getattr(request.user, 'student_profile', None)
    teacher = getattr(request.user, 'teacher_profile', None)
    grade = str(min(level.number, 3))
    subject_rows = []

    for subject in subjects:
        if student:
            plans = LessonPlan.objects.filter(
                assignments__student=student,
                assignments__is_active=True,
                level=level,
                subject=subject,
                is_active=True,
            ).select_related('teacher', 'subject', 'level').distinct()[:3]
        elif teacher:
            plans = LessonPlan.objects.filter(
                teacher=teacher,
                level=level,
                subject=subject,
                is_active=True,
            ).select_related('teacher', 'subject', 'level')[:3]
        else:
            plans = LessonPlan.objects.filter(
                level=level,
                subject=subject,
                status__in=(LessonPlan.Status.ACTIVE, LessonPlan.Status.IN_PROGRESS),
                is_active=True,
            ).select_related('teacher', 'subject', 'level')[:2]

        resource_grade = student.grade if student else grade
        activity_count = Activity.objects.filter(is_active=True, level=level, subject=subject, grade=resource_grade).count()
        reading_count = Reading.objects.filter(is_active=True, level=level, subject=subject, grade=resource_grade).count()
        game_queryset = Game.objects.filter(is_active=True, level=level, subject=subject)
        game_count = games_for_student(game_queryset, student).count() if student else game_queryset.filter(grade=resource_grade).count()
        correct_answers = 0
        total_answers = 0
        if student:
            from games.models import GameAttemptAnswer
            answers = GameAttemptAnswer.objects.filter(attempt__student=student, attempt__game__level=level, subject=subject.name)
            total_answers = answers.count()
            correct_answers = answers.filter(is_correct=True).count()

        subject_rows.append({
            'subject': subject,
            'grade': grade,
            'activities_count': activity_count,
            'readings_count': reading_count,
            'games_count': game_count,
            'total_resources': activity_count + reading_count + game_count,
            'plans': plans,
            'correct_answers': correct_answers,
            'total_answers': total_answers,
        })

    assigned_plan_count = 0
    if student:
        assigned_plan_count = LessonPlanAssignment.objects.filter(student=student, plan__level=level, is_active=True).count()

    return render(request, 'learning/level_detail.html', {
        'level': level,
        'grade': grade,
        'subject_rows': subject_rows,
        'assigned_plan_count': assigned_plan_count,
        'student': student,
        'teacher': teacher,
    })
