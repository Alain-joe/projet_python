"""
projet_cimetiere/cemeterre_backend/cemetery/api_cemetery.py
API pour la gestion du cimetière.
CORRECTION : Ajout de jwt_auth_or_query_param sur l'endpoint /config/ pour la carte.
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from django.db.models import Count, Q
import math

# ✅ IMPORT DE LA FONCTION D'AUTHENTIFICATION FLEXIBLE
from .api_graves import jwt_auth_or_query_param

from .models import Cemetery, Grave, Section, Allee
from .schemas import (
    CemeteryIn, CemeteryUpdate, CemeteryOut,
    AlleeIn, AlleeOut,
    CemeteryInitializationSchema
)
from .geometry_service import GeometryService
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Cemeteries"])


@router.get("/cemeteries/", response=list[CemeteryOut])
def list_cemeteries(request):
    return Cemetery.objects.all()


@router.get("/config/", response=CemeteryOut, auth=jwt_auth_or_query_param) # ✅ CORRECTION ICI
def get_cemetery_config(request):
    """Récupère la configuration du cimetière unique avec ses limites (bounds) pour la carte."""
    cemetery = Cemetery.objects.first()
    if not cemetery:
        return {"error": "Aucun cimetière configuré. Veuillez initialiser la configuration."}

    bounds = None
    if cemetery.latitude and cemetery.longitude and cemetery.longueur_totale and cemetery.largeur_totale:
        delta_lat = (cemetery.largeur_totale / 2) / 111000
        delta_lng = (cemetery.longueur_totale / 2) / (111000 * math.cos(math.radians(cemetery.latitude)))

        bounds = {
            "north": cemetery.latitude + delta_lat,
            "south": cemetery.latitude - delta_lat,
            "east": cemetery.longitude + delta_lng,
            "west": cemetery.longitude - delta_lng,
        }

    return {
        "id": cemetery.id,
        "name": cemetery.name,
        "city": cemetery.city,
        "address": cemetery.address,
        "latitude": cemetery.latitude,
        "longitude": cemetery.longitude,
        "total_area": cemetery.total_area,
        "non_exploitable_area": cemetery.non_exploitable_area,
        "longueur_totale": cemetery.longueur_totale,
        "largeur_totale": cemetery.largeur_totale,
        "grave_length": cemetery.grave_length,
        "grave_width": cemetery.grave_width,
        "espacement_caveaux": cemetery.espacement_caveaux,
        "calculated_capacity": cemetery.calculated_capacity,
        "created_at": cemetery.created_at,
        "updated_at": cemetery.updated_at,
        "bounds": bounds,
    }


@router.post("/cemeteries/initialize-complete/")
@require_role("admin")
def initialize_cemetery_complete(request, data: CemeteryInitializationSchema):
    cemetery = Cemetery.objects.first()

    if cemetery:
        for field, value in data.cemetery.dict(exclude_unset=True).items():
            setattr(cemetery, field, value)
        cemetery.save()
    else:
        cemetery = Cemetery.objects.create(**data.cemetery.dict())

    print(f"🧹 Nettoyage des anciennes sections et allées pour le cimetière {cemetery.id}...")
    Allee.objects.filter(cemetery=cemetery).delete()
    Section.objects.filter(cemetery=cemetery).delete()

    bounds = GeometryService.calculate_cemetery_bounds(
        cemetery.latitude,
        cemetery.longitude,
        cemetery.longueur_totale,
        cemetery.largeur_totale
    )

    cemetery_polygon = GeometryService.create_cemetery_polygon(bounds)
    allee_polygons = []
    created_allees = []

    for allee_data in data.allees:
        allee = Allee.objects.create(
            cemetery=cemetery,
            nom=allee_data.nom,
            type_allee=allee_data.type_allee,
            largeur=allee_data.largeur,
            coordinates=allee_data.coordinates
        )

        allee_polygon = GeometryService.create_allee_polygon_meters(
            allee_data.coordinates,
            allee_data.largeur
        )

        if allee_polygon:
            allee_polygons.append(allee_polygon)
            allee.surface_calculee = allee_polygon.area
            allee.save()

        created_allees.append({
            "id": allee.id,
            "nom": allee.nom,
            "surface": allee.surface_calculee
        })

    sections_polygons = GeometryService.split_cemetery_by_allees(
        cemetery_polygon,
        allee_polygons
    )

    created_sections = []
    section_names = data.section_names or []

    for i, section_polygon in enumerate(sections_polygons, start=1):
        surface = abs(section_polygon.area)

        coords = GeometryService.polygon_to_coords(
            section_polygon,
            cemetery.latitude,
            cemetery.longitude
        )

        capacite = GeometryService.calculate_grave_capacity(
            surface,
            cemetery.grave_length,
            cemetery.grave_width,
            cemetery.espacement_caveaux
        )

        if i <= len(section_names):
            name = section_names[i - 1]
        else:
            name = GeometryService.generate_section_name(i)

        section = Section.objects.create(
            cemetery=cemetery,
            name=name,
            is_exploitable=True,
            polygon_coords=coords,
            surface_calculee=surface,
            capacite_caveaux=capacite,
            ordre=i,
            longueur=0,
            largeur=0,
            zone_non_exploitable=0
        )

        created_sections.append({
            "id": section.id,
            "nom": section.name,
            "surface": round(surface, 2),
            "capacite": capacite
        })

    total_capacity = sum(s["capacite"] for s in created_sections)
    cemetery.calculated_capacity = total_capacity
    cemetery.save()

    return {
        "message": "Cimetière initialisé avec succès",
        "cemetery_id": cemetery.id,
        "cemetery_name": cemetery.name,
        "surface_totale": cemetery.total_area,
        "surface_exploitable": sum(s["surface"] for s in created_sections),
        "capacite_totale": total_capacity,
        "allees_creees": len(created_allees),
        "sections_creees": len(created_sections),
        "allees": created_allees,
        "sections": created_sections
    }


@router.put("/cemeteries/{cemetery_id}/")
@require_role("admin")
def update_cemetery(request, cemetery_id: int, data: CemeteryUpdate):
    cemetery = get_object_or_404(Cemetery, id=cemetery_id)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(cemetery, field, value)

    cemetery.save()

    return {
        "message": "Configuration du cimetière mise à jour",
        "calculated_capacity": cemetery.calculated_capacity
    }


@router.get("/stats/")
def get_cemetery_stats(request):
    cemetery = Cemetery.objects.first()
    if not cemetery:
        return {"error": "Aucun cimetière configuré"}

    total_graves = Grave.objects.count()
    available_graves = Grave.objects.filter(status='available').count()
    reserved_graves = Grave.objects.filter(status='reserved').count()
    occupied_graves = Grave.objects.filter(status='occupied').count()

    occupation_rate = (occupied_graves / total_graves * 100) if total_graves > 0 else 0

    return {
        "cemetery_id": cemetery.id,
        "cemetery_name": cemetery.name,
        "theoretical_capacity": cemetery.calculated_capacity,
        "total_graves_created": total_graves,
        "available": available_graves,
        "reserved": reserved_graves,
        "occupied": occupied_graves,
        "occupation_rate": round(occupation_rate, 2),
        "saturation_warning": occupation_rate > 80
    }


@router.get("/allees/", response=list[AlleeOut])
def list_allees(request, cemetery_id: int = None):
    queryset = Allee.objects.all()
    if cemetery_id:
        queryset = queryset.filter(cemetery_id=cemetery_id)
    return queryset


@router.get("/allees/geojson/")
def get_allees_geojson(request):
    cemetery = Cemetery.objects.first()
    if not cemetery:
        return {"type": "FeatureCollection", "features": []}

    allees = Allee.objects.filter(cemetery=cemetery)

    features = []
    for allee in allees:
        if allee.coordinates:
            coords = [[lng, lat] for lat, lng in allee.coordinates]

            features.append({
                "type": "Feature",
                "properties": {
                    "id": allee.id,
                    "nom": allee.nom,
                    "type": allee.type_allee,
                    "largeur": allee.largeur,
                    "surface": allee.surface_calculee
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/sections/geojson/")
def get_sections_geojson(request):
    cemetery = Cemetery.objects.first()
    if not cemetery:
        return {"type": "FeatureCollection", "features": []}

    sections = Section.objects.filter(cemetery=cemetery, is_exploitable=True)

    features = []
    for section in sections:
        if section.polygon_coords:
            coords = [[lng, lat] for lat, lng in section.polygon_coords]

            features.append({
                "type": "Feature",
                "properties": {
                    "id": section.id,
                    "nom": section.name,
                    "surface": section.surface_calculee,
                    "capacite": section.capacite_caveaux,
                    "ordre": section.ordre
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }