import secrets

from django.db import migrations, models

import learning.models

ALPHABET = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'


def assign_codes(apps, schema_editor):
    TeacherProfile = apps.get_model('learning', 'TeacherProfile')
    used = set()
    for teacher in TeacherProfile.objects.all().only('pk'):
        code = ''.join(secrets.choice(ALPHABET) for _ in range(6))
        while code in used:
            code = ''.join(secrets.choice(ALPHABET) for _ in range(6))
        used.add(code)
        TeacherProfile.objects.filter(pk=teacher.pk).update(classroom_code=code)


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0016_lessonplanassignment_is_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherprofile',
            name='classroom_code',
            field=models.CharField(editable=False, max_length=6, null=True, verbose_name='Código de aula'),
        ),
        migrations.RunPython(assign_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='teacherprofile',
            name='classroom_code',
            field=models.CharField(default=learning.models.generate_classroom_code, editable=False, max_length=6, unique=True, verbose_name='Código de aula'),
        ),
    ]
