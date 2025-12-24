from django.core.management.base import BaseCommand
from django.utils import timezone
from game.models import Zone, Team
import datetime

class Command(BaseCommand):
    help = 'Update scores based on zone ownership'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        zones = Zone.objects.filter(status='OWNED')
        
        for zone in zones:
            if zone.last_score_update:
                # Calculate minutes since last update
                diff = now - zone.last_score_update
                minutes = int(diff.total_seconds() / 60)
                
                if minutes >= 1:
                    zone.owner.score += minutes
                    zone.owner.save()
                    zone.last_score_update = now # Reset update time or adjust
                    # Better: last_score_update += timedelta(minutes=minutes) to keep precision
                    zone.last_score_update += datetime.timedelta(minutes=minutes)
                    zone.save()
                    self.stdout.write(self.style.SUCCESS(f"Added {minutes} points to {zone.owner.name} for {zone.name}"))
            else:
                zone.last_score_update = now
                zone.save()
