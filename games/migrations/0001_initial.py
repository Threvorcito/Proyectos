import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('learning', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=120)),
                ('slug', models.SlugField(unique=True)),
                ('description', models.TextField()),
                ('skill', models.CharField(max_length=120)),
                ('game_type', models.CharField(choices=[('letter_hunter', 'Cazador de letras'), ('build_word', 'Construye la palabra'), ('listen_find', 'Escucha y encuentra'), ('memory', 'Memoria de palabras'), ('letter_detective', 'Detective de letras'), ('reading_path', 'Camino de lectura')], max_length=40)),
                ('icon', models.CharField(default='🎮', max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('level', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='games', to='learning.level')),
            ],
        ),
        migrations.CreateModel(
            name='GameAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.PositiveSmallIntegerField(default=0)),
                ('correct_answers', models.PositiveSmallIntegerField(default=0)),
                ('total_questions', models.PositiveSmallIntegerField(default=0)),
                ('completed', models.BooleanField(default=False)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='attempts', to='games.game')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='game_attempts', to='learning.studentprofile')),
            ],
            options={
                'ordering': ['-started_at'],
            },
        ),
    ]
