from django.db import models
from django.utils import timezone

class Team(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Game(models.Model):
    is_active = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)
    mode = models.CharField(
        max_length=8,
        choices=[('STANDARD', 'Standard'), ('FREE', 'Free'), ('QR', 'QR')],
        default='STANDARD',
    )
    accepted_distance = models.FloatField(default=5)
    top_left_longitude = models.FloatField(default=0.0)
    top_left_latitude = models.FloatField(default=0.0)
    bottom_right_longitude = models.FloatField(default=0.0)
    bottom_right_latitude = models.FloatField(default=0.0)
    end_bonus_applied = models.BooleanField(default=False)

    def __str__(self):
        return f"Game {self.id} ({'Active' if self.is_active else 'Inactive'})"

class Zone(models.Model):
    STATUS_CHOICES = [
        ('NEUTRAL', 'Neutral'),
        ('CAPTURING', 'Capturing'),
        ('OWNED', 'Owned'),
        ('CONTESTED', 'Contested'),
    ]

    name = models.CharField(max_length=100)
    longitude = models.FloatField(default=0.0)
    latitude = models.FloatField(default=0.0)
    is_base = models.BooleanField(default=False)
    adjacent_zones = models.ManyToManyField('self', blank=True, symmetrical=True)
    
    # Admin can color each place as he wants (maybe initial color or neutral color)
    default_color = models.CharField(max_length=20, default='#FFFFFF')

    owner = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_zones')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='NEUTRAL')
    
    capturing_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True, related_name='capturing_zones')
    capture_started_at = models.DateTimeField(null=True, blank=True)
    
    # For point calculation
    last_score_update = models.DateTimeField(null=True, blank=True)
    # Used for recapture scoring: min(minutes since last loss, 5)
    last_lost_at = models.DateTimeField(null=True, blank=True)
    last_lost_by_team_name = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return self.name


class GameSnapshot(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='snapshots')
    minute_index = models.IntegerField()
    captured_at = models.DateTimeField(default=timezone.now)
    scores = models.JSONField(default=dict)
    zones = models.JSONField(default=list)

    class Meta:
        unique_together = ('game', 'minute_index')
        ordering = ['minute_index']

    def __str__(self):
        return f"Snapshot m{self.minute_index} @ {self.captured_at}"
