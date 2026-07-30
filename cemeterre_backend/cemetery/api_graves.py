"""
cemetery/api_graves.py — Endpoints pour la gestion des caveaux.
Compatible Django Ninja + JWT.
CORRECTION : Ajout de jwt_auth_or_query_param pour permettre le token en URL (pour la carte).
"""
import math
from ninja import Router, Schema
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from .models import Grave, Section
from .schemas import GraveIn, GraveUpdate, GraveOut, GenerateGridSchema
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Graves"])

# ==============================================================================
# FONCTION D'AUTHENTIFICATION FLEXIBLE (Header OU Query Param)
# ==============================================================================
def jwt_auth_or_query_param(request):
    """Authentifie via le header Authorization OU via le paramètre ?token=... dans l'URL."""
    try:
        user = JWTAuth().authenticate(request)
        if user:
            return user
    except Exception:
        pass
    
    token = request.GET.get("token")
    if token:
        try:
            from ninja_jwt.tokens import AccessToken
            from django.contrib.auth import get_user_model
            valid_token = AccessToken(token)
            User = get_user_model()
            return User.objects.get(id=valid_token["user_id"])
        except Exception:
            raise HttpError(401, "Token d'authentification invalide ou expiré.")
    raise HttpError(401, "Non authentifié. Token manquant.")


# ==============================================================================
# 1. ROUTES STATIQUES (SANS PARAMÈTRE DYNAMIQUE)
# ==============================================================================

@router.get("/graves", response=list[GraveOut])
@router.get("/graves/", response=list[GraveOut])
def list_graves(request, section_id: int = None, status: str = None):
    queryset = Grave.objects.all().select_related("section")
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


@router.get("/graves/disponibles", response=list[GraveOut])
def get_available_graves(request, section_id: int = None):
    queryset = Grave.objects.filter(status="available").select_related("section")
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    return queryset


@router.get("/graves-geojson/", auth=jwt_auth_or_query_param) # ✅ CORRECTION ICI
def get_graves_geojson(request):
    """Endpoint optimisé pour la carte Leaflet (format GeoJSON)."""
    graves = Grave.objects.select_related("section__cemetery").all()
    
    features = []
    for grave in graves:
        if grave.location:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [grave.location.x, grave.location.y]
                },
                "properties": {
                    "id": grave.id,
                    "code": grave.code,
                    "status": grave.status,
                    "section": grave.section.name if grave.section else "Inconnue",
                    "price": f"{int(grave.price):,}".replace(",", " ") if grave.price else "0",
                    "grave_type": grave.grave_type or "Simple"
                }
            })
    
    return {
        "type": "FeatureCollection",
        "features": features
    }


@router.get("/graves-map", auth=jwt_auth_or_query_param)
def get_graves_for_map(request, cemetery_id: int = None):
    graves = Grave.objects.select_related("section__cemetery").all()
    if cemetery_id:
        graves = graves.filter(section__cemetery_id=cemetery_id)

    result = []
    for grave in graves:
        lat = grave.location.y if grave.location else None
        lng = grave.location.x if grave.location else None
        result.append({
            "id": grave.id,
            "code": grave.code,
            "status": grave.status,
            "latitude": lat,
            "longitude": lng,
            "section": grave.section.name if grave.section else "Inconnue",
            "price": float(grave.price) if grave.price else 0.0,
            "grave_type": grave.grave_type or "Simple"
        })
    return {"count": len(result), "graves": result}


@router.post("/graves/generate-grid")
@require_role("admin", "agent")
def generate_graves_grid(request, data: GenerateGridSchema):
    section = get_object_or_404(Section, id=data.section_id)
    created_count = 0
    counter = 1
    
    lat_offset_per_m = 1.0 / 111111.0
    lng_offset_per_m = 1.0 / (111111.0 * math.cos(math.radians(data.start_lat)))
    
    for r in range(data.rows):
        for c in range(data.cols):
            current_lat = data.start_lat - (r * data.spacing_meters * lat_offset_per_m)
            current_lng = data.start_lng + (c * data.spacing_meters * lng_offset_per_m)
            
            base_code = f"{data.prefix}-{counter:03d}"
            code = base_code
            suffix = 1
            
            while Grave.objects.filter(code=code).exists():
                code = f"{data.prefix}-{counter:03d}-{suffix}"
                suffix += 1
            
            Grave.objects.create(
                section=section,
                code=code,
                status="available",
                grave_type="simple",
                length=section.cemetery.grave_length,
                width=section.cemetery.grave_width,
                capacity=1,
                price=data.price,
                location=Point(current_lng, current_lat, srid=4326)
            )
            created_count += 1
            counter += 1
            
    return {
        "message": f"{created_count} caveaux générés avec succès dans la section '{section.name}'.",
        "created_count": created_count,
        "section_id": section.id,
        "sample_codes": [f"{data.prefix}-{i:03d}" for i in range(1, min(6, created_count + 1))]
    }


@router.post("/graves")
@require_role("admin", "agent")
def create_grave(request, data: GraveIn):
    location = None
    if data.latitude is not None and data.longitude is not None:
        location = Point(data.longitude, data.latitude, srid=4326)
    
    grave = Grave.objects.create(
        section_id=data.section_id,
        code=data.code,
        status=data.status or "available",
        grave_type=data.grave_type,
        length=data.length,
        width=data.width,
        capacity=data.capacity,
        price=data.price,
        notes=data.notes,
        location=location
    )
    return {"grave_id": grave.id, "message": "Caveau créé avec succès"}


# ==============================================================================
# 2. ROUTES DYNAMIQUES (AVEC {grave_id})
# ==============================================================================

@router.get("/graves/{grave_id}", response=GraveOut)
def get_grave(request, grave_id: int):
    return get_object_or_404(Grave, id=grave_id)


@router.put("/graves/{grave_id}")
@require_role("admin", "agent")
def update_grave(request, grave_id: int, data: GraveUpdate):
    grave = get_object_or_404(Grave, id=grave_id)
    
    update_fields = []
    for field, value in data.dict(exclude_unset=True).items():
        if field not in ["latitude", "longitude"]:
            setattr(grave, field, value)
            update_fields.append(field)
    
    if data.latitude is not None and data.longitude is not None:
        grave.location = Point(data.longitude, data.latitude, srid=4326)
        update_fields.append("location")
    
    grave.save(update_fields=update_fields)
    return {"message": "Caveau mis à jour avec succès"}


@router.delete("/graves/{grave_id}")
@require_role("admin")
def delete_grave(request, grave_id: int):
    grave = get_object_or_404(Grave, id=grave_id)
    
    if hasattr(grave, "concession") and grave.concession and grave.concession.status == "active":
        return {"error": "Impossible de supprimer : ce caveau a une concession active"}
    
    grave.delete()
    return {"message": "Caveau supprimé"}