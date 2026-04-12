from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Zone, Team, Game
import math
import json

map_width, map_height = 1189, 1140  # Example dimensions for coordinate calculations


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2)**2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c  * 1000 # distance in m

def index(request):
    teams = Team.objects.all()
    return render(request, 'game/index.html', {'teams': teams})

def map_view(request, role):
    game, _ = Game.objects.get_or_create(id=1)
    mean_lat = (game.top_left_latitude + game.bottom_right_latitude) / 2
    scale = math.cos(math.radians(mean_lat))

    game.diameter = 2 * round(game.accepted_distance * math.sqrt(map_height**2 + map_width**2) / haversine(game.top_left_latitude, game.top_left_longitude, game.bottom_right_latitude, game.bottom_right_longitude))

    if role == 'admin' and request.method == 'POST':
        start_time_str = request.POST.get('start_time')
        duration = request.POST.get('duration')
        
        if start_time_str and duration:
            try:
                # datetime-local format: YYYY-MM-DDTHH:MM
                start_time = timezone.datetime.fromisoformat(start_time_str)
                if timezone.is_naive(start_time):
                    start_time = timezone.make_aware(start_time)
                
                game.start_time = start_time
                game.duration_minutes = int(duration)
                game.end_time = start_time + timezone.timedelta(minutes=int(duration))
                game.save()
            except ValueError:
                pass

    zones = Zone.objects.all()
    for zone in zones:
        zone.x_coordinate = (
            (zone.longitude - game.top_left_longitude) * scale
            / ((game.bottom_right_longitude - game.top_left_longitude) * scale)
            * map_width
        )

        zone.y_coordinate = (
            (game.top_left_latitude - zone.latitude)
            / (game.top_left_latitude - game.bottom_right_latitude)
            * map_height
        )    
        
    capturing_zones = Zone.objects.filter(status='CAPTURING')
    teams = Team.objects.all()
    
    from django.conf import settings
    context = {
        'role': role,
        'zones': zones,
        'capturing_zones': capturing_zones,
        'game': game,
        'teams': teams,
        'TIME_ZONE': settings.TIME_ZONE,
    }
    return render(request, 'game/map.html', context)

def is_connected_to_base(team, target_zone):
    """
    Check if the target_zone is reachable from any of the team's bases.
    Reachable means there is a path of zones OWNED by the team from a base to the target_zone.
    """
    bases = Zone.objects.filter(owner=team, is_base=True)
    if not bases.exists():
        return False
    
    # BFS to find all reachable zones owned by team
    queue = list(bases)
    visited = set(b.id for b in bases)
    reachable_zones = set(b.id for b in bases)
    
    while queue:
        current = queue.pop(0)
        # Get neighbors that are also owned by the team
        neighbors = current.adjacent_zones.filter(owner=team)
        for neighbor in neighbors:
            if neighbor.id not in visited:
                visited.add(neighbor.id)
                reachable_zones.add(neighbor.id)
                queue.append(neighbor)
                
    return target_zone.id in reachable_zones

def can_interact(team, zone, game_mode='standard'):
    """
    Determines if a team can interact with a zone (attack or defend).
    Rule: Teams can attack only places adjacent to their ones which are path connected with their base.
          Same for defending (must be connected to base).
    """
    if game_mode.lower() == 'free':
        return True  # In free mode, any interaction is allowed
    
    # 1. Calculate the set of all zones owned by team that are connected to a base
    bases = Zone.objects.filter(owner=team, is_base=True)
    if not bases.exists():
        return False

    queue = list(bases)
    visited = set(b.id for b in bases)
    connected_owned_zones_ids = set(b.id for b in bases)

    while queue:
        current = queue.pop(0)
        # Traverse only through owned zones
        neighbors = current.adjacent_zones.filter(owner=team)
        for neighbor in neighbors:
            if neighbor.id not in visited:
                visited.add(neighbor.id)
                connected_owned_zones_ids.add(neighbor.id)
                queue.append(neighbor)

    # 2. Check if the target zone is valid
    # Case A: Defending/Interacting with own zone -> Must be in the connected set
    if zone.id in connected_owned_zones_ids:
        return True
    
    # Case B: Attacking -> Must be adjacent to a zone in the connected set
    # Check if any neighbor of 'zone' is in 'connected_owned_zones_ids'
    # We can query the DB or check IDs if we pre-fetched adjacency (but here we query)
    is_adjacent_to_connected = zone.adjacent_zones.filter(id__in=connected_owned_zones_ids).exists()
    
    return is_adjacent_to_connected

def zone_click(request, zone_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        role = data.get('role')
        longitude = data.get('longitude')
        latitude = data.get('latitude')

        
        if role == 'admin':
            # Admin logic (e.g., change color)
            return JsonResponse({'status': 'admin_action'})
        
        if longitude is None or latitude is None:
            return JsonResponse({'error': 'Missing GPS coordinates'}, status=400)
        
        # Check Game Time
        game = Game.objects.first()
        now = timezone.now()
        if not game or not game.start_time or not game.end_time:
             return JsonResponse({'error': 'Game not configured'}, status=400)
        if now < game.start_time:
             return JsonResponse({'error': f'Game has not started yet. Start: {game.start_time}, Now: {now}'}, status=400)
        if now > game.end_time:
             return JsonResponse({'error': f'Game is over. End: {game.end_time}, Now: {now}'}, status=400)
            
        try:
            team = Team.objects.get(name__iexact=role)
        except Team.DoesNotExist:
            return JsonResponse({'error': 'Invalid team'}, status=400)
            
        zone = get_object_or_404(Zone, id=zone_id)

        if haversine(latitude, longitude, zone.latitude, zone.longitude) > game.accepted_distance:
            return JsonResponse({'error': 'You are too far from the zone to interact'}, status=400)
        
        if zone.is_base:
            return JsonResponse({'error': 'Cannot capture base'}, status=400)

        # Check connectivity rules
        if not can_interact(team, zone, game.mode):
             return JsonResponse({'error': 'Zone is not reachable from your base!'}, status=400)

        # Game logic
        if zone.status == 'NEUTRAL':
            zone.status = 'CAPTURING'
            zone.capturing_team = team
            zone.capture_started_at = timezone.now()
            zone.save()
            return JsonResponse({'status': 'capturing_started', 'team': team.name})
            
        elif zone.status == 'CAPTURING':
            if zone.capturing_team == team:
                return JsonResponse({'status': 'already_capturing'})
            else:
                # Hostile team stops it
                if zone.owner:
                    zone.status = 'OWNED'
                else:
                    zone.status = 'NEUTRAL'
                
                zone.capturing_team = None
                zone.capture_started_at = None
                zone.save()
                return JsonResponse({'status': 'capture_stopped'})
                
        elif zone.status == 'OWNED':
            if zone.owner == team:
                return JsonResponse({'status': 'already_owned'})
            else:
                # Hostile team attacks owned zone
                zone.status = 'CAPTURING'
                # Owner remains until capture is complete
                zone.capturing_team = team
                zone.capture_started_at = timezone.now()
                zone.save()
                return JsonResponse({'status': 'capturing_started', 'team': team.name})
                
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'error': 'Method not allowed'}, status=405)

