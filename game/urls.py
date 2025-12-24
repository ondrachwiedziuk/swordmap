from django.urls import path
from . import views
from . import views_api

urlpatterns = [
    path('', views.index, name='index'),
    path('map/<str:role>/', views.map_view, name='map'),
    path('api/zone/<int:zone_id>/click/', views.zone_click, name='zone_click'),
    path('api/state/', views_api.game_state, name='game_state'),
]
