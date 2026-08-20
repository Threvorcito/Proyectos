from django.utils import timezone

from activities.models import Activity
from learning.models import StudentProfile

from .models import ActivityAttempt, StudentDifficulty, StudentProgress


SIMILAR_LETTER_PAIRS = (('b', 'd'), ('p', 'q'), ('m', 'n'), ('u', 'n'))


def detect_difficulty(activity: Activity, answer: str, correct_answer: str = ''):
    activity_type = activity.activity_type
    normalized_answer = (answer or '').strip().lower()
    normalized_correct = (correct_answer or '').strip().lower()
    if activity_type in (Activity.ActivityType.FIND_LETTER, Activity.ActivityType.SIMILAR_LETTERS):
        for character_a, character_b in SIMILAR_LETTER_PAIRS:
            if {normalized_answer, normalized_correct} == {character_a, character_b}:
                return {
                    'difficulty_type': 'letter_confusion',
                    'character_a': character_a,
                    'character_b': character_b,
                    'word': normalized_answer,
                }
        return {'difficulty_type': 'letter_confusion', 'character_a': normalized_answer[:1], 'word': normalized_answer}
    if activity_type == Activity.ActivityType.SYLLABLES:
        return {'difficulty_type': 'syllable_confusion', 'syllable': normalized_answer[:20], 'word': normalized_answer}
    if activity_type in (Activity.ActivityType.LISTEN_SELECT, Activity.ActivityType.READING):
        return {'difficulty_type': 'phonological_awareness', 'word': normalized_answer}
    return {'difficulty_type': 'activity_error', 'word': normalized_answer}


def register_attempt(user, activity: Activity, answer: str, is_correct: bool, correct_answer: str = ''):
    student = user.student_profile
    last_attempt = ActivityAttempt.objects.filter(student=student, activity=activity).order_by('-attempt_number').first()
    attempt_number = 1 if last_attempt is None else last_attempt.attempt_number + 1
    attempt = ActivityAttempt.objects.create(
        student=student,
        activity=activity,
        answer=answer,
        is_correct=is_correct,
        attempt_number=attempt_number,
    )
    progress, _ = StudentProgress.objects.get_or_create(student=student, activity=activity)
    progress.attempts = attempt_number
    progress.completed = progress.completed or is_correct
    progress.progress_percentage = min(100, progress.progress_percentage + (20 if is_correct else 5))
    progress.best_score = max(progress.best_score, 100 if is_correct else 0)
    progress.last_activity_date = timezone.now()
    progress.save()
    student.last_activity_at = timezone.now()
    student.save(update_fields=['last_activity_at'])
    if not is_correct:
        difficulty_data = detect_difficulty(activity, answer, correct_answer)
        difficulty, _ = StudentDifficulty.objects.get_or_create(student=student, **difficulty_data)
        difficulty.error_count += 1
        difficulty.save()
    else:
        student.points += activity.points
        student.stars += activity.stars
        student.experience += activity.points
        student.save(update_fields=['points', 'stars', 'experience'])
    return attempt
