from learning.models import StudentProfile
from progress.models import StudentDifficulty


def get_recommended_activities(student: StudentProfile):
    current_level = student.current_level or student.reading_level
    if current_level is None:
        return []
    queryset = current_level.activities.filter(is_active=True, grade=student.grade).order_by('id')
    if not queryset.exists():
        queryset = current_level.activities.filter(is_active=True).order_by('id')
    difficulties = StudentDifficulty.objects.filter(student=student).order_by('-error_count')
    if difficulties.exists():
        top = difficulties.first()
        if top.difficulty_type == 'letter_confusion':
            return queryset.filter(activity_type__in=['FIND_LETTER', 'SIMILAR_LETTERS'])
        if top.difficulty_type == 'syllable_confusion':
            return queryset.filter(activity_type='SYLLABLES')
        if top.difficulty_type == 'phonological_awareness':
            return queryset.filter(activity_type__in=['LISTEN_SELECT', 'READING'])
    return queryset[:3]
