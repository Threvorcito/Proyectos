from django.db import transaction
from django.db.models import F, Max
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
    """Record an answer and update progress atomically.

    The student row is locked for the whole transaction so concurrent submissions
    for the same student are serialized (attempt numbers, progress and points
    stay consistent). Points, stars and experience are awarded only the first
    time the activity flips to completed. The returned attempt carries
    ``points_awarded`` so callers can tell the student whether they earned points.
    """
    now = timezone.now()
    with transaction.atomic():
        student = StudentProfile.objects.select_for_update().get(pk=user.student_profile.pk)
        last_number = (
            ActivityAttempt.objects.filter(student=student, activity=activity)
            .aggregate(last=Max('attempt_number'))['last']
        ) or 0
        attempt = ActivityAttempt.objects.create(
            student=student,
            activity=activity,
            answer=answer,
            is_correct=is_correct,
            attempt_number=last_number + 1,
        )
        progress, _ = StudentProgress.objects.get_or_create(student=student, activity=activity)
        first_completion = is_correct and not progress.completed
        progress.attempts = attempt.attempt_number
        progress.completed = progress.completed or is_correct
        progress.progress_percentage = min(100, progress.progress_percentage + (20 if is_correct else 5))
        progress.best_score = max(progress.best_score, 100 if is_correct else 0)
        progress.last_activity_date = now
        progress.save()

        update_fields = {'last_activity_at': now}
        if first_completion:
            update_fields.update(
                points=F('points') + activity.points,
                stars=F('stars') + activity.stars,
                experience=F('experience') + activity.points,
            )
        StudentProfile.objects.filter(pk=student.pk).update(**update_fields)

        if not is_correct:
            difficulty_data = detect_difficulty(activity, answer, correct_answer)
            difficulty, _ = StudentDifficulty.objects.get_or_create(student=student, **difficulty_data)
            StudentDifficulty.objects.filter(pk=difficulty.pk).update(error_count=F('error_count') + 1, last_error_date=now)
    attempt.points_awarded = activity.points if first_completion else 0
    return attempt
