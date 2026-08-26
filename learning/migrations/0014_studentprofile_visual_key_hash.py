from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('learning', '0013_academic_relationships'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='visual_key_hash',
            field=models.CharField(blank=True, max_length=128),
        ),
    ]
