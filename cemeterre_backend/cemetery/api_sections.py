# projet_cimetiere/cemeterre_backend/cemetery/api_sections.py

from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from .models import Section, Cemetery
from .schemas import SectionIn, SectionUpdate, SectionOut
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Sections"])


@router.get("/sections", response=list[SectionOut])
def list_sections(request, cemetery_id: int = None):
    """Lister les sections avec leur capacité calculée"""
    queryset = Section.objects.select_related("cemetery").all()
    if cemetery_id:
        queryset = queryset.filter(cemetery_id=cemetery_id)
    
    result = []
    for section in queryset:
        section_data = {
            "id": section.id,
            "cemetery_id": section.cemetery.id,
            "name": section.name,
            "is_exploitable": section.is_exploitable,
            "description": section.description,
            "longueur": section.longueur,
            "largeur": section.largeur,
            "zone_non_exploitable": section.zone_non_exploitable,
            "capacity": section.calculate_capacity(),
            "created_at": section.created_at
        }
        result.append(section_data)
    
    return result


@router.post("/sections")
@require_role("admin")
def create_section(request, data: SectionIn):
    """Créer une nouvelle section (admin uniquement)"""
    cemetery = get_object_or_404(Cemetery, id=data.cemetery_id)
    
    section = Section.objects.create(
        cemetery=cemetery,
        name=data.name,
        is_exploitable=data.is_exploitable,
        description=data.description or "",
        longueur=data.longueur,
        largeur=data.largeur,
        zone_non_exploitable=data.zone_non_exploitable
    )
    
    return {
        "id": section.id,
        "name": section.name,
        "cemetery_id": section.cemetery.id,
        "capacity": section.calculate_capacity(),
        "message": "Section créée avec succès"
    }


@router.get("/sections/{section_id}", response=SectionOut)
def get_section(request, section_id: int):
    """Obtenir les détails d'une section"""
    section = get_object_or_404(Section, id=section_id)
    return {
        "id": section.id,
        "cemetery_id": section.cemetery.id,
        "name": section.name,
        "is_exploitable": section.is_exploitable,
        "description": section.description,
        "longueur": section.longueur,
        "largeur": section.largeur,
        "zone_non_exploitable": section.zone_non_exploitable,
        "capacity": section.calculate_capacity(),
        "created_at": section.created_at
    }


@router.put("/sections/{section_id}")
@require_role("admin")
def update_section(request, section_id: int, data: SectionUpdate):
    """Modifier une section (admin uniquement)"""
    section = get_object_or_404(Section, id=section_id)
    
    for field, value in data.dict(exclude_unset=True).items():
        setattr(section, field, value)
    
    section.save()
    return {
        "message": "Section mise à jour",
        "capacity": section.calculate_capacity()
    }


@router.delete("/sections/{section_id}")
@require_role("admin")
def delete_section(request, section_id: int):
    """Supprimer une section (admin uniquement)"""
    section = get_object_or_404(Section, id=section_id)
    
    if section.graves.exists():
        return {"error": "Impossible de supprimer : des caveaux sont associés à cette section"}
    
    section.delete()
    return {"message": "Section supprimée"}