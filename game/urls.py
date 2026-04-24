from django.urls import path
from . import views
from . import views_api

urlpatterns = [
    path('', views.index, name='index'),
    path('rules/', views.rules_view, name='rules'),
    path('stats/', views.stats_view, name='stats'),
    path('map/<str:role>/', views.map_view, name='map'),
    path('api/zone/<int:zone_id>/click/', views.zone_click, name='zone_click'),
    path('api/zone/scan-qr/', views.zone_scan_qr, name='zone_scan_qr'),
    path('api/state/', views_api.game_state, name='game_state'),
    path('api/stats/timeline/', views_api.stats_timeline, name='stats_timeline'),
    path('c/<str:code>', views.qr_link, name='qr_link'),
]
