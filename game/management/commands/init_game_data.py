from django.core.management.base import BaseCommand
from game.models import Team, Zone, Game
import json
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Initialize game data'

    def handle(self, *args, **kwargs):
        # Ensure Game instance exists
        Game.objects.get_or_create(id=1)
        self.stdout.write(self.style.SUCCESS("Game instance created/exists"))

        # Load zones from config
        config_path = os.path.join(settings.BASE_DIR, 'game_config.json')
        if not os.path.exists(config_path):
            self.stdout.write(self.style.ERROR(f"Config file not found at {config_path}"))
            return

        with open(config_path, 'r') as f:
            config = json.load(f)

        # 1. Extract Teams from Bases
        teams_config = {}
        for zone_data in config.get('zones', []):
            if zone_data.get('is_base') and zone_data.get('owner'):
                team_name = zone_data['owner']
                team_color = zone_data.get('color', '#FFFFFF') # Use base color as team color
                teams_config[team_name] = team_color

        # 2. Create/Update Teams
        current_team_names = []
        for name, color in teams_config.items():
            Team.objects.update_or_create(name=name, defaults={'color': color, 'score': 0})
            current_team_names.append(name)
            self.stdout.write(self.style.SUCCESS(f"Team {name} processed (Score reset)"))

        # Delete teams that are no longer in the config
        deleted_teams_count, _ = Team.objects.exclude(name__in=current_team_names).delete()
        if deleted_teams_count > 0:
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_teams_count} old teams"))

        processed_zone_names = []
        for zone_data in config.get('zones', []):
            defaults = {
                'x_coordinate': zone_data['x'],
                'y_coordinate': zone_data['y'],
                'default_color': zone_data['color'],
                'is_base': zone_data.get('is_base', False),
                # Reset game state
                'owner': None,
                'status': 'NEUTRAL',
                'capturing_team': None,
                'capture_started_at': None,
                'last_score_update': None
            }
            
            if zone_data.get('owner'):
                try:
                    team = Team.objects.get(name__iexact=zone_data['owner'])
                    defaults['owner'] = team
                    defaults['status'] = 'OWNED'
                except Team.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Team {zone_data['owner']} not found for zone {zone_data['name']}"))

            zone, created = Zone.objects.update_or_create(
                id=zone_data.get('id'), # Use ID from config if available, or let DB assign (but we prefer explicit ID)
                defaults={**defaults, 'name': zone_data['name']} # Name is now in defaults to allow ID lookup
            )
            processed_zone_names.append(zone.name)
            self.stdout.write(self.style.SUCCESS(f"Zone {zone.name} {'created' if created else 'updated'}"))

        # Validate adjacency symmetry in config
        zones_dict = {z['id']: set(z.get('adjacent_zones', [])) for z in config.get('zones', [])}
        for z_id, adj_ids in zones_dict.items():
            for adj_id in adj_ids:
                if adj_id not in zones_dict:
                    self.stdout.write(self.style.ERROR(f"Zone {z_id} refers to non-existent zone {adj_id}"))
                    continue
                if z_id not in zones_dict[adj_id]:
                    self.stdout.write(self.style.WARNING(f"Asymmetry detected: Zone {z_id} -> {adj_id}, but {adj_id} does not list {z_id}. Fixing automatically."))
                    zones_dict[adj_id].add(z_id)

        # Second pass: Link adjacent zones
        for zone_data in config.get('zones', []):
            z_id = zone_data.get('id')
            if z_id in zones_dict:
                zone = Zone.objects.get(id=z_id)
                adjacent_ids = zones_dict[z_id]
                adjacent_zones = Zone.objects.filter(id__in=adjacent_ids)
                zone.adjacent_zones.set(adjacent_zones)
                self.stdout.write(self.style.SUCCESS(f"Linked {zone.name} to {list(adjacent_zones.values_list('name', flat=True))}"))

        # Delete zones that are not in the config
        deleted_count, _ = Zone.objects.exclude(name__in=processed_zone_names).delete()
        if deleted_count > 0:
            self.stdout.write(self.style.WARNING(f"Deleted {deleted_count} old zones not present in config"))
