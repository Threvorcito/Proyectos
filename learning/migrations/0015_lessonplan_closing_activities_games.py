from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0001_initial'),
        ('learning', '0014_studentprofile_visual_key_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='lessonplan',
            name='closing_activities',
            field=models.TextField(blank=True, verbose_name='Actividades de cierre/evaluación'),
        ),
        migrations.AddField(
            model_name='lessonplan',
            name='games',
            field=models.ManyToManyField(blank=True, related_name='lesson_plans', to='games.game'),
        ),
    ]
