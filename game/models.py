from django.db import models
from django.utils import timezone

class Team(models.Model):
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(max_length=20, unique=True)
    score = models.IntegerField(default=0)

    def __str__(self):
        return self.name

class Game(models.Model):
    is_active = models.BooleanField(default=False)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    duration_minutes = models.IntegerField(default=60)

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
    x_coordinate = models.FloatField(default=0.0)
    y_coordinate = models.FloatField(default=0.0)
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

    def __str__(self):
        return self.name
