from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('game', '0009_game_end_bonus_and_zone_loss_tracking'),
    ]

    operations = [
        migrations.CreateModel(
            name='GameSnapshot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('minute_index', models.IntegerField()),
                ('captured_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('scores', models.JSONField(default=dict)),
                ('zones', models.JSONField(default=list)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='snapshots', to='game.game')),
            ],
            options={
                'ordering': ['minute_index'],
                'unique_together': {('game', 'minute_index')},
            },
        ),
    ]
