# projet_cimetiere/cemeterre_backend/cemetery/views.py

from django.shortcuts import render
from django.http import JsonResponse
from .models import Grave, Cemetery

def map_view(request):
    """
    Affiche la page HTML de la carte interactive Leaflet.
    Le token est passé en paramètre GET pour permettre au JS d'authentifier les actions.
    """
    token = request.GET.get('token', '')
    return render(request, 'cemetery/map.html', {
        'token': token
    })
def map_setup_view(request):
    """
    Affiche la page HTML de configuration des allées (dessin sur carte Leaflet).
    Les paramètres (lat, lng, name, city, token, etc.) sont transmis en query string
    par la vue Flet alleys_setup.py et lus côté client en JavaScript
    via URLSearchParams — pas besoin de les injecter dans le contexte Django.
    """
    return render(request, 'cemetery/map_setup.html')

def graves_geojson(request):
    """Renvoie les caveaux au format GeoJSON standard pour Leaflet"""
    graves = Grave.objects.select_related('section__cemetery').all()
    
    features = []
    for grave in graves:
        lng = grave.location.x if grave.location else 11.8750
        lat = grave.location.y if grave.location else -4.7878
        
        features.append({
            "type": "Feature",
            "properties": {
                "id": grave.id,
                "code": grave.code,
                "status": grave.status or "available",
                "price": float(grave.price or 0),
                "section": grave.section.name if grave.section else "Inconnue",
                "grave_type": grave.grave_type or "Simple"
            },
            "geometry": {
                "type": "Point",
                "coordinates": [lng, lat]
            }
        })
    
    return JsonResponse({
        "type": "FeatureCollection",
        "features": features
    })

# ... (autres fonctions existantes)

def cemetery_config(request):
    """
    Renvoie la configuration du cimetière (singleton).
    Accessible sans authentification forte pour la carte.
    """
    try:
        cemetery = Cemetery.objects.first()
        if not cemetery:
            return JsonResponse({"error": "Aucun cimetière configuré"}, status=404)
        
        # Utiliser la méthode du modèle pour calculer les bornes
        rect = cemetery.get_rectangle_coordinates()
        
        return JsonResponse({
            "id": cemetery.id,
            "name": cemetery.name,
            "city": cemetery.city,
            "total_area": cemetery.total_area,
            "latitude": cemetery.latitude,
            "longitude": cemetery.longitude,
            "longueur_totale": cemetery.longueur_totale,
            "largeur_totale": cemetery.largeur_totale,
            "bounds": rect["bounds"] if rect else None,
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)