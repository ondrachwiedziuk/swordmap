from django.core.management.base import BaseCommand
from django.utils import timezone
from game.models import Zone, Team, Game
import datetime
import time

class Command(BaseCommand):
    help = 'Process game state: update scores and handle captures'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting game state processor loop...")
        while True:
            now = timezone.now()
            
            # Check Game Status
            game = Game.objects.first()
            if not game:
                self.stdout.write(self.style.WARNING("No game instance found. Retrying in 5s..."))
                time.sleep(5)
                continue

            if not game.start_time or not game.end_time:
                 self.stdout.write(self.style.WARNING("Game start/end time not set. Retrying in 5s..."))
                 time.sleep(5)
                 continue

            if now < game.start_time:
                 self.stdout.write(self.style.WARNING(f"Game has not started yet. Starts at {game.start_time}. Waiting..."))
                 time.sleep(5)
                 continue
            
            if now > game.end_time:
                 self.stdout.write(self.style.WARNING(f"Game has ended. Ended at {game.end_time}"))
                 time.sleep(10)
                 continue

            # 1. Handle Captures
            capturing_zones = Zone.objects.filter(status='CAPTURING')
            for zone in capturing_zones:
                if zone.capture_started_at:
                    diff = now - zone.capture_started_at
                    if diff.total_seconds() >= 60: # 1 minute
                        zone.status = 'OWNED'
                        zone.owner = zone.capturing_team
                        
                        # Reward for capturing
                        zone.owner.score += 5
                        zone.owner.save()
                        
                        zone.capturing_team = None
                        zone.capture_started_at = None
                        zone.last_score_update = now
                        zone.save()
                        self.stdout.write(self.style.SUCCESS(f"Zone {zone.name} captured by {zone.owner.name} (+5 points)"))

            # 2. Update Scores
            # Points are counted for each minute holding the point of interest (excluding bases)
            owned_zones = Zone.objects.filter(status='OWNED', is_base=False)
            for zone in owned_zones:
                if zone.last_score_update:
                    diff = now - zone.last_score_update
                    minutes = int(diff.total_seconds() / 60)
                    
                    if minutes >= 1:
                        zone.owner.score += minutes
                        zone.owner.save()
                        zone.last_score_update += datetime.timedelta(minutes=minutes)
                        zone.save()
                        self.stdout.write(self.style.SUCCESS(f"Added {minutes} points to {zone.owner.name} for {zone.name}"))
                else:
                    zone.last_score_update = now
                    zone.save()
            
            time.sleep(1)
