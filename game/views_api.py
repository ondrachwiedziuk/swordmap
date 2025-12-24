from django.http import JsonResponse
from django.utils import timezone
from .models import Zone, Team, Game

def game_state(request):
    zones = Zone.objects.all()
    capturing_zones = Zone.objects.filter(status='CAPTURING')
    teams = Team.objects.all()
    game = Game.objects.first()
    
    scores = {team.name: {'score': team.score, 'color': team.color} for team in teams}
    
    zones_data = {}
    for zone in zones:
        owner_color = zone.owner.color if zone.owner else zone.default_color
        
        capturing_color = None
        if zone.status == 'CAPTURING' and zone.capturing_team:
            capturing_color = zone.capturing_team.color

        zones_data[zone.id] = {
            'id': zone.id,
            'color': owner_color,
            'owner': zone.owner.name if zone.owner else None,
            'is_capturing': zone.status == 'CAPTURING',
            'capturing_color': capturing_color,
            'is_base': zone.is_base
        }
        
    capturing_data = []
    now = timezone.now()
    
    game_remaining_seconds = 0
    if game and game.end_time:
        if now < game.end_time:
             game_remaining_seconds = int((game.end_time - now).total_seconds())
        else:
             game_remaining_seconds = 0

    for zone in capturing_zones:
        remaining = 0
        if zone.capture_started_at:
            elapsed = (now - zone.capture_started_at).total_seconds()
            remaining = max(0, 60 - int(elapsed))
            
        capturing_data.append({
            'name': zone.name,
            'team_name': zone.capturing_team.name,
            'team_color': zone.capturing_team.color,
            'remaining_seconds': remaining
        })
        
    return JsonResponse({
        'zones': zones_data,
        'capturing': capturing_data,
        'scores': scores,
        'game_remaining_seconds': game_remaining_seconds
    })
