from django.urls import path
from . import views

urlpatterns = [
    path('map/', views.map_view, name='cemetery_map'),
    path('graves-geojson/', views.graves_geojson, name='graves_geojson'),
    # ✅ AJOUT DE CETTE LIGNE :
    path('config/', views.cemetery_config, name='cemetery_config'),
]