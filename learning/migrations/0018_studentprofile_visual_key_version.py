from django.db import migrations, models


class Migration(migrations.Migration):
    """Existing keys are three ordered drawings (v1); new keys are two-of-nine pairs (v2)."""

    dependencies = [
        ('learning', '0017_teacherprofile_classroom_code'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='visual_key_version',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
