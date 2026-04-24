from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0008_alter_game_mode'),
    ]

    operations = [
        migrations.AddField(
            model_name='game',
            name='end_bonus_applied',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='zone',
            name='last_lost_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='zone',
            name='last_lost_by_team_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
