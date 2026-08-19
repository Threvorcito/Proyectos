from django.db import migrations, models
from django.db.models import Count, Q


def deduplicate_teacher_emails(apps, schema_editor):
    TeacherProfile = apps.get_model('learning', 'TeacherProfile')
    duplicate_emails = (
        TeacherProfile.objects.exclude(email='')
        .values('email')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )
    for row in duplicate_emails:
        duplicates = list(TeacherProfile.objects.filter(email=row['email']).order_by('id'))
        for duplicate in duplicates[1:]:
            duplicate.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0005_teacherprofile_password'),
    ]

    operations = [
        migrations.RunPython(deduplicate_teacher_emails, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='teacherprofile',
            constraint=models.UniqueConstraint(
                condition=~Q(email=''),
                fields=('email',),
                name='unique_teacher_email_when_present',
            ),
        ),
    ]
