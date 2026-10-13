from django.db import migrations, models
from django.db.models import Count


def merge_duplicate_rows(apps, schema_editor):
    """Merge duplicates so the unique constraints can be added safely.

    The oldest row (lowest id) of each group is kept. StudentProgress keeps the
    most advanced values (completed if any row was, max percentage, score,
    attempts and latest activity date). StudentDifficulty sums error counts and
    keeps the latest error date. Extra rows are deleted.
    """
    StudentProgress = apps.get_model('progress', 'StudentProgress')
    StudentDifficulty = apps.get_model('progress', 'StudentDifficulty')

    progress_groups = (
        StudentProgress.objects.values('student_id', 'activity_id')
        .annotate(row_count=Count('id'))
        .filter(row_count__gt=1)
    )
    for group in progress_groups:
        rows = list(StudentProgress.objects.filter(student_id=group['student_id'], activity_id=group['activity_id']).order_by('id'))
        keeper, extras = rows[0], rows[1:]
        dates = [row.last_activity_date for row in rows if row.last_activity_date]
        StudentProgress.objects.filter(pk=keeper.pk).update(
            completed=any(row.completed for row in rows),
            progress_percentage=max(row.progress_percentage for row in rows),
            best_score=max(row.best_score for row in rows),
            attempts=max(row.attempts for row in rows),
            last_activity_date=max(dates) if dates else None,
        )
        StudentProgress.objects.filter(pk__in=[row.pk for row in extras]).delete()

    key_fields = ('student_id', 'difficulty_type', 'character_a', 'character_b', 'syllable', 'word')
    difficulty_groups = (
        StudentDifficulty.objects.values(*key_fields)
        .annotate(row_count=Count('id'))
        .filter(row_count__gt=1)
    )
    for group in difficulty_groups:
        lookup = {field: group[field] for field in key_fields}
        rows = list(StudentDifficulty.objects.filter(**lookup).order_by('id'))
        keeper, extras = rows[0], rows[1:]
        StudentDifficulty.objects.filter(pk=keeper.pk).update(
            error_count=sum(row.error_count for row in rows),
            last_error_date=max(row.last_error_date for row in rows),
        )
        StudentDifficulty.objects.filter(pk__in=[row.pk for row in extras]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('progress', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(merge_duplicate_rows, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='studentprogress',
            constraint=models.UniqueConstraint(fields=('student', 'activity'), name='unique_progress_per_student_activity'),
        ),
        migrations.AddConstraint(
            model_name='studentdifficulty',
            constraint=models.UniqueConstraint(
                fields=('student', 'difficulty_type', 'character_a', 'character_b', 'syllable', 'word'),
                name='unique_difficulty_per_student_pattern',
            ),
        ),
    ]
