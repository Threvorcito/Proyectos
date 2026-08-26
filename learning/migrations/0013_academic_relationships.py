from django.db import migrations, models


def backfill_teacher_students(apps, schema_editor):
    LessonPlanAssignment = apps.get_model('learning', 'LessonPlanAssignment')
    TeacherProfile = apps.get_model('learning', 'TeacherProfile')
    through_model = TeacherProfile.students.through
    db_alias = schema_editor.connection.alias

    relationships = (
        LessonPlanAssignment.objects.using(db_alias)
        .filter(plan__teacher_id__isnull=False, student_id__isnull=False)
        .values_list('plan__teacher_id', 'student_id')
        .distinct()
    )
    for teacher_id, student_id in relationships:
        through_model.objects.using(db_alias).get_or_create(
            teacherprofile_id=teacher_id,
            studentprofile_id=student_id,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0012_lessonplan_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='students',
            field=models.ManyToManyField(blank=True, related_name='teachers', to='learning.studentprofile'),
        ),
        migrations.AddField(
            model_name='parentprofile',
            name='students',
            field=models.ManyToManyField(blank=True, related_name='parents', to='learning.studentprofile'),
        ),
        migrations.RunPython(backfill_teacher_students, migrations.RunPython.noop),
    ]
