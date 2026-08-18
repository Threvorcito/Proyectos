from learning.models import StudentProfile
from progress.models import StudentDifficulty


def get_recommended_activities(student: StudentProfile):
    queryset = student.current_level.activities.filter(is_active=True).order_by('id')
    difficulties = StudentDifficulty.objects.filter(student=student).order_by('-error_count')
    if difficulties.exists():
        top = difficulties.first()
        if top.difficulty_type == 'letter_confusion':
            return queryset.filter(activity_type__in=['FIND_LETTER', 'SIMILAR_LETTERS'])
        if top.difficulty_type == 'syllable_confusion':
            return queryset.filter(activity_type='SYLLABLES')
    return queryset[:3]
