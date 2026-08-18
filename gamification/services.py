from .models import Achievement, StudentAchievement


def evaluate_achievements(student):
    earned = set(StudentAchievement.objects.filter(student=student).values_list('achievement_id', flat=True))
    for achievement in Achievement.objects.all():
        if achievement.id in earned:
            continue
        if achievement.requirement_type == 'activities' and student.progress_items.filter(completed=True).count() >= achievement.requirement_value:
            StudentAchievement.objects.create(student=student, achievement=achievement)
        elif achievement.requirement_type == 'readings' and achievement.requirement_value <= 10:
            StudentAchievement.objects.create(student=student, achievement=achievement)
        elif achievement.requirement_type == 'streak' and student.learning_streak >= achievement.requirement_value:
            StudentAchievement.objects.create(student=student, achievement=achievement)
