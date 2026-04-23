from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import Zone, Team, Game
import math
import json
import re
import hashlib
from urllib.parse import quote, unquote

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

    map_diagonal_distance = haversine(
        game.top_left_latitude,
        game.top_left_longitude,
        game.bottom_right_latitude,
        game.bottom_right_longitude,
    )
    if map_diagonal_distance > 0:
        game.diameter = 2 * round(
            game.accepted_distance
            * math.sqrt(map_height**2 + map_width**2)
            / map_diagonal_distance
        )
    else:
        game.diameter = 0

    if role == 'admin2536' and request.method == 'POST':
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
    longitude_span = (game.bottom_right_longitude - game.top_left_longitude) * scale
    latitude_span = game.top_left_latitude - game.bottom_right_latitude
    for zone in zones:
        if longitude_span:
            zone.x_coordinate = (
                (zone.longitude - game.top_left_longitude) * scale
                / longitude_span
                * map_width
            )
        else:
            zone.x_coordinate = map_width / 2

        if latitude_span:
            zone.y_coordinate = (
                (game.top_left_latitude - zone.latitude)
                / latitude_span
                * map_height
            )
        else:
            zone.y_coordinate = map_height / 2
        
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
    response = render(request, 'game/map.html', context)
    if role != 'admin2536':
        response.set_cookie('swordmap_team', quote(role), max_age=60 * 60 * 24)
    return response

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


def process_zone_interaction(team, zone):
    # Game logic shared by GPS and QR flows.
    if zone.status == 'NEUTRAL':
        zone.status = 'CAPTURING'
        zone.capturing_team = team
        zone.capture_started_at = timezone.now()
        zone.save()
        return JsonResponse({'status': 'capturing_started', 'team': team.name})

    if zone.status == 'CAPTURING':
        if zone.capturing_team == team:
            return JsonResponse({'status': 'already_capturing'})

        # Hostile team stops it
        if zone.owner:
            zone.status = 'OWNED'
        else:
            zone.status = 'NEUTRAL'

        zone.capturing_team = None
        zone.capture_started_at = None
        zone.save()
        return JsonResponse({'status': 'capture_stopped'})

    if zone.status == 'OWNED':
        if zone.owner == team:
            return JsonResponse({'status': 'already_owned'})

        # Hostile team attacks owned zone
        zone.status = 'CAPTURING'
        # Owner remains until capture is complete
        zone.capturing_team = team
        zone.capture_started_at = timezone.now()
        zone.save()
        return JsonResponse({'status': 'capturing_started', 'team': team.name})

    return JsonResponse({'status': 'ok'})


QR_SECRET = "swordmap-tajny-klic"
QR_BASE_URL = "https://smazeny.pull.cz/c/"


def make_signature(zone_id: str) -> str:
    return hashlib.sha256(f"{zone_id}-{QR_SECRET}".encode()).hexdigest()[:3].upper()


def parse_zone_id_from_qr(qr_code):
    """Parse a QR URL like https://smazeny.pull.cz/c/<zone_id><3-char-signature>.

    Returns the integer zone_id on success, None on failure.
    """
    if not qr_code:
        return None

    raw = str(qr_code).strip()

    # Strip the base URL prefix.
    if raw.startswith(QR_BASE_URL):
        raw = raw[len(QR_BASE_URL):]
    elif raw.startswith("http"):
        # Wrong domain / path – reject.
        return None

    if len(raw) < 4:
        # Need at least 1 char zone_id + 3 char signature.
        return None

    zone_id_part = raw[:-3]
    sig_part = raw[-3:]

    expected_sig = make_signature(zone_id_part)
    if sig_part.upper() != expected_sig:
        return None

    # zone_id_part may be a plain integer or a spare code like "S1".
    if zone_id_part.isdigit():
        return int(zone_id_part)

    return None

def zone_click(request, zone_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
        role = data.get('role')
        longitude = data.get('longitude')
        latitude = data.get('latitude')

        
        if role == 'admin2536':
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

        if game.mode == 'QR':
            return JsonResponse({'error': 'QR mode is active. Capture zones by scanning QR codes.'}, status=400)
            
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

        return process_zone_interaction(team, zone)
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def zone_scan_qr(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON payload'}, status=400)
    role = data.get('role')
    qr_code = data.get('qr_code')

    if role == 'admin2536':
        return JsonResponse({'status': 'admin_action'})

    if not qr_code:
        return JsonResponse({'error': 'Missing QR code value'}, status=400)

    game = Game.objects.first()
    now = timezone.now()
    if not game or not game.start_time or not game.end_time:
        return JsonResponse({'error': 'Game not configured'}, status=400)
    if now < game.start_time:
        return JsonResponse({'error': f'Game has not started yet. Start: {game.start_time}, Now: {now}'}, status=400)
    if now > game.end_time:
        return JsonResponse({'error': f'Game is over. End: {game.end_time}, Now: {now}'}, status=400)

    if game.mode != 'QR':
        return JsonResponse({'error': 'QR capture is available only when game mode is QR.'}, status=400)

    try:
        team = Team.objects.get(name__iexact=role)
    except Team.DoesNotExist:
        return JsonResponse({'error': 'Invalid team'}, status=400)

    zone_id = parse_zone_id_from_qr(qr_code)
    if zone_id is None:
        return JsonResponse({'error': 'Invalid QR code – bad URL or signature.'}, status=400)

    zone = get_object_or_404(Zone, id=zone_id)

    if zone.is_base:
        return JsonResponse({'error': 'Cannot capture base'}, status=400)

    if not can_interact(team, zone, game.mode):
        return JsonResponse({'error': 'Zone is not reachable from your base!'}, status=400)

    response = process_zone_interaction(team, zone)
    response.set_cookie('swordmap_team', quote(team.name), max_age=60 * 60 * 24)
    return response


def _do_qr_capture(team, zone, game):
    """Attempt capture and return a redirect response to the map (with team cookie set)."""
    if not can_interact(team, zone, game.mode):
        return None, 'Zone is not reachable from your base!'

    process_zone_interaction(team, zone)
    response = redirect('map', role=team.name.lower())
    response.set_cookie('swordmap_team', quote(team.name), max_age=60 * 60 * 24)
    return response, None


def qr_link(request, code):
    """Handle direct QR link opened from an external QR scanner app.

    URL: /c/<zone_id><signature>

    If the team is cached in a cookie, capture immediately and redirect to map.
    Otherwise show team-selection; on POST store the cookie and redirect to map.
    """
    qr_url = QR_BASE_URL + code
    zone_id = parse_zone_id_from_qr(qr_url)

    if zone_id is None:
        return render(request, 'game/qr_capture.html', {
            'error': 'Invalid QR code.',
        })

    zone = get_object_or_404(Zone, id=zone_id)
    teams = Team.objects.all()

    game = Game.objects.first()
    now = timezone.now()

    # Validate game state.
    game_error = None
    if not game or not game.start_time or not game.end_time:
        game_error = 'Game not configured.'
    elif now < game.start_time:
        game_error = 'Game has not started yet.'
    elif now > game.end_time:
        game_error = 'Game is over.'
    elif game.mode != 'QR':
        game_error = 'QR capture is not active right now.'

    if game_error:
        return render(request, 'game/qr_capture.html', {
            'error': game_error,
            'zone': zone,
        })

    if zone.is_base:
        return render(request, 'game/qr_capture.html', {
            'error': 'Cannot capture a base zone.',
            'zone': zone,
        })

    # --- Try cached team (cookie) on GET ---
    if request.method == 'GET':
        cached_team_name = unquote(request.COOKIES.get('swordmap_team', '')).strip()
        if cached_team_name:
            try:
                team = Team.objects.get(name__iexact=cached_team_name)
                response, error = _do_qr_capture(team, zone, game)
                if response:
                    return response
                # Capture failed (unreachable) – fall through to team picker
                # with the error so the user sees what happened.
                return render(request, 'game/qr_capture.html', {
                    'error': error,
                    'zone': zone,
                    'teams': teams,
                    'code': code,
                })
            except Team.DoesNotExist:
                pass  # stale cookie – fall through to team picker

    # --- POST: explicit team selection ---
    if request.method == 'POST':
        team_name = request.POST.get('team', '').strip()
        try:
            team = Team.objects.get(name__iexact=team_name)
        except Team.DoesNotExist:
            return render(request, 'game/qr_capture.html', {
                'error': 'Invalid team.',
                'zone': zone,
                'teams': teams,
                'code': code,
            })

        response, error = _do_qr_capture(team, zone, game)
        if response:
            return response
        return render(request, 'game/qr_capture.html', {
            'error': error,
            'zone': zone,
            'teams': teams,
            'code': code,
        })

    # GET without cached team – show team picker.
    return render(request, 'game/qr_capture.html', {
        'zone': zone,
        'teams': teams,
        'code': code,
    })
