from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_login_attempt'),
    ]

    operations = [
        migrations.AddField(
            model_name='loginattempt',
            name='lockouts',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='loginattempt',
            name='lockouts_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='loginattempt',
            name='requires_unlock',
            field=models.BooleanField(default=False),
        ),
    ]
