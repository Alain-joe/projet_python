"""
projet_cimetiere/cemeterre_backend/cemetery/api_inhumations.py
Gestion des inhumations et recherche de défunts.
CORRECTION : Gestion de heure_inhumation dans create_inhumation
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, time

from .models import Inhumation, Grave, Concession
from .schemas import InhumationIn, InhumationOut
from users.models import User
from core.permissions import require_role
from core.audit import log_action

router = Router(auth=JWTAuth(), tags=["Inhumations"])


@router.get("/inhumations", response=list[InhumationOut])
@require_role("admin", "secretariat", "agent")
def list_inhumations(request, search: str = None):
    queryset = Inhumation.objects.select_related("grave", "agent_inhumation").all()
    if search:
        queryset = queryset.filter(
            Q(defunt_nom__icontains=search) |
            Q(defunt_prenom__icontains=search) |
            Q(grave__code__icontains=search)
        )
    return queryset.order_by("-date_inhumation")


@router.get("/inhumations/search", response=list[InhumationOut])
@require_role("admin", "secretariat")
def search_inhumations(request, nom: str = None, prenom: str = None, date_deces: str = None):
    queryset = Inhumation.objects.select_related("grave", "concession", "agent_inhumation")
    
    if nom:
        queryset = queryset.filter(defunt_nom__icontains=nom)
    if prenom:
        queryset = queryset.filter(defunt_prenom__icontains=prenom)
    if date_deces:
        queryset = queryset.filter(defunt_date_deces=date_deces)
        
    return queryset.order_by("-date_inhumation")[:20]


@router.post("/inhumations", response=InhumationOut)
@require_role("admin", "secretariat", "agent")
def create_inhumation(request, data: InhumationIn):
    grave = get_object_or_404(Grave, id=data.grave_id)
    
    concession = None
    if data.concession_id:
        concession = get_object_or_404(Concession, id=data.concession_id)
        
    agent = None
    if data.agent_inhumation_id:
        agent = get_object_or_404(User, id=data.agent_inhumation_id)
    else:
        agent = request.auth

    # ✅ CORRECTION : Combiner date et heure si fournies
    date_inhumation = timezone.now()
    if data.heure_inhumation:
        try:
            h, m = map(int, data.heure_inhumation.split(":"))
            date_inhumation = datetime.combine(date_inhumation.date(), time(h, m), tzinfo=timezone.utc)
        except ValueError:
            pass

    inhumation = Inhumation.objects.create(
        grave=grave,
        concession=concession,
        reservation_id=data.reservation_id,
        defunt_prenom=data.defunt_prenom,
        defunt_nom=data.defunt_nom,
        defunt_date_naissance=data.defunt_date_naissance,
        defunt_date_deces=data.defunt_date_deces,
        agent_inhumation=agent,
        observations=data.observations or "",
        date_inhumation=date_inhumation,
    )
    
    if grave.status in ["available", "reserved"]:
        grave.status = "occupied"
        grave.last_status_change = timezone.now()
        grave.save()

    log_action(request.auth, "create", "Inhumation", inhumation.id, f"Inhumation au caveau {grave.code}")
    
    return inhumation


@router.get("/inhumations/{inhumation_id}", response=InhumationOut)
@require_role("admin", "secretariat", "agent")
def get_inhumation(request, inhumation_id: int):
    return get_object_or_404(
        Inhumation.objects.select_related("grave", "concession", "agent_inhumation"), 
        id=inhumation_id
    )