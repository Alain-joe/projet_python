# projet_cimetiere/cemeterre_backend/cemetery/api_graves.py

import math
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point
from .models import Grave, Section
from .schemas import GraveIn, GraveUpdate, GraveOut, GenerateGridSchema
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Graves"])

# ==============================================================================
# 1. ROUTES STATIQUES (SANS PARAMÈTRE DYNAMIQUE) - À METTRE EN PREMIER !
# ==============================================================================

@router.get("/graves", response=list[GraveOut])
def list_graves(request, section_id: int = None, status: str = None):
    """Lister tous les caveaux avec filtres optionnels"""
    queryset = Grave.objects.all().select_related("section")
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    if status:
        queryset = queryset.filter(status=status)
    return queryset


@router.get("/graves/disponibles", response=list[GraveOut])
def get_available_graves(request, section_id: int = None):
    """Récupérer tous les caveaux DISPONIBLES (status='available') - exclut les non exploitables"""
    queryset = Grave.objects.filter(status="available").select_related("section")
    if section_id:
        queryset = queryset.filter(section_id=section_id)
    return queryset


@router.get("/graves-map")
def get_graves_for_map(request, cemetery_id: int = None):
    """Endpoint optimisé pour la carte Leaflet."""
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
    """
    Génère automatiquement une grille de caveaux avec leurs coordonnées GPS PostGIS.
    Calcule les positions en convertissant les mètres en degrés géographiques.
    """
    section = get_object_or_404(Section, id=data.section_id)
    
    created_count = 0
    counter = 1
    
    # Conversion approximative : 1 degré de latitude ≈ 111,111 mètres
    lat_offset_per_m = 1.0 / 111111.0
    lng_offset_per_m = 1.0 / (111111.0 * math.cos(math.radians(data.start_lat)))
    
    for r in range(data.rows):
        for c in range(data.cols):
            current_lat = data.start_lat - (r * data.spacing_meters * lat_offset_per_m)
            current_lng = data.start_lng + (c * data.spacing_meters * lng_offset_per_m)
            
            base_code = f"{data.prefix}-{counter:03d}"
            code = base_code
            suffix = 1
            
            # Sécurité : si le code existe déjà, on ajoute un suffixe
            while Grave.objects.filter(code=code).exists():
                code = f"{data.prefix}-{counter:03d}-{suffix}"
                suffix += 1
            
            # Création du caveau avec son PointField PostGIS
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
    """Créer un nouveau caveau avec géolocalisation PostGIS"""
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
# 2. ROUTES DYNAMIQUES (AVEC {grave_id}) - À METTRE EN DERNIER !
# ==============================================================================

@router.get("/graves/{grave_id}", response=GraveOut)
def get_grave(request, grave_id: int):
    """Obtenir les détails d'un caveau spécifique"""
    return get_object_or_404(Grave, id=grave_id)


@router.put("/graves/{grave_id}")
@require_role("admin", "agent")
def update_grave(request, grave_id: int, data: GraveUpdate):
    """Modifier un caveau (admin/agent uniquement)"""
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
    """Supprimer un caveau (admin uniquement)"""
    grave = get_object_or_404(Grave, id=grave_id)
    
    if hasattr(grave, "concession") and grave.concession and grave.concession.status == "active":
        return {"error": "Impossible de supprimer : ce caveau a une concession active"}
    
    grave.delete()
    return {"message": "Caveau supprimé"}