"""
projet_cimetiere/cemeterre_backend/cemetery/api_graves_signalements.py
API pour la gestion des signalements de caveaux non exploitables.
Workflow : Agent signale → Admin valide/rejette → Caveau devient non exploitable si validé.
"""

from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Grave, CaveauSignalement
from .schemas import (
    SignalerProblemeSchema,
    ValiderSignalementSchema,
    RejeterSignalementSchema,
    CaveauSignalementSchema
)
from core.permissions import require_role
from core.audit import log_action
from notifications.utils_extended import notifier_nouveau_signalement_caveau

router = Router(auth=JWTAuth(), tags=["Graves Signalements"])


@router.post("/graves/{grave_id}/signaler-probleme/", response=CaveauSignalementSchema)
@require_role("agent", "admin")
def signaler_probleme_caveau(request, grave_id: int, data: SignalerProblemeSchema):
    """
    Un agent signale un problème sur un caveau.
    Le statut du signalement est 'en_attente' jusqu'à validation par l'admin.
    """
    grave = get_object_or_404(Grave, id=grave_id)
    
    # Vérifier que le caveau n'est pas déjà non exploitable
    if grave.status == 'non_exploitable':
        raise HttpError(400, "Ce caveau est déjà marqué comme non exploitable.")
    
    signalement = CaveauSignalement.objects.create(
        grave=grave,
        motif=data.motif,
        description=data.description or "",
        signale_par=request.auth,
        photos=data.photos
    )
    
    # Notifier les administrateurs
    try:
        notifier_nouveau_signalement_caveau(signalement)
    except Exception as e:
        print(f"⚠️ Erreur notification signalement: {e}")
    
    # Journal d'audit
    log_action(
        request.auth,
        "create",
        "CaveauSignalement",
        signalement.id,
        f"Signalement créé pour caveau {grave.code}: {data.motif}"
    )
    
    return signalement


@router.get("/graves/signalements/", response=list[CaveauSignalementSchema])
@require_role("admin", "secretariat", "agent")
def list_signalements(request, statut: str = None, grave_id: int = None):
    """
    Liste tous les signalements avec filtres optionnels.
    - Admin/Secrétariat : voit tous les signalements
    - Agent : voit uniquement ses propres signalements
    """
    queryset = CaveauSignalement.objects.all().select_related("grave", "signale_par", "valide_par")
    
    if statut:
        queryset = queryset.filter(statut=statut)
    
    if grave_id:
        queryset = queryset.filter(grave_id=grave_id)
    
    # Si l'utilisateur est un agent (non admin), filtrer sur ses propres signalements
    if request.auth.role == "agent":
        queryset = queryset.filter(signale_par=request.auth)
    
    return queryset


@router.get("/graves/signalements/{signalement_id}", response=CaveauSignalementSchema)
@require_role("admin", "secretariat", "agent")
def get_signalement(request, signalement_id: int):
    """Récupère les détails d'un signalement spécifique"""
    signalement = get_object_or_404(
        CaveauSignalement.objects.select_related("grave", "signale_par", "valide_par"),
        id=signalement_id
    )
    
    # Vérification des permissions
    if request.auth.role == "agent" and signalement.signale_par != request.auth:
        raise HttpError(403, "Accès refusé : ce signalement ne vous appartient pas.")
    
    return signalement


@router.post("/graves/signalements/{signalement_id}/valider/", response=CaveauSignalementSchema)
@require_role("admin")
def valider_signalement(request, signalement_id: int, data: ValiderSignalementSchema = None):
    """
    L'administrateur valide un signalement.
    Actions :
    - Le statut du signalement passe à 'valide'
    - Le caveau devient 'non_exploitable'
    - Le motif est enregistré sur le caveau
    - Le caveau disparaît des résultats de réservation
    """
    signalement = get_object_or_404(CaveauSignalement, id=signalement_id)
    
    if signalement.statut != 'en_attente':
        raise HttpError(400, f"Ce signalement a déjà été traité (statut: {signalement.statut}).")
    
    # Mettre à jour le signalement
    signalement.statut = 'valide'
    signalement.valide_par = request.auth
    signalement.date_validation = timezone.now()
    signalement.save()
    
    # Mettre à jour le caveau
    grave = signalement.grave
    grave.status = 'non_exploitable'
    grave.motif_non_exploitable = signalement.motif
    grave.date_non_exploitable = timezone.now()
    grave.non_exploitable_par = request.auth
    grave.last_status_change = timezone.now()
    grave.save()
    
    # Journal d'audit
    log_action(
        request.auth,
        "status_change",
        "Grave",
        grave.id,
        f"Caveau {grave.code} déclaré non exploitable. Motif: {signalement.motif}"
    )
    
    return signalement


@router.post("/graves/signalements/{signalement_id}/rejeter/", response=CaveauSignalementSchema)
@require_role("admin")
def rejeter_signalement(request, signalement_id: int, data: RejeterSignalementSchema):
    """
    L'administrateur rejette un signalement.
    Le caveau conserve son statut actuel.
    """
    signalement = get_object_or_404(CaveauSignalement, id=signalement_id)
    
    if signalement.statut != 'en_attente':
        raise HttpError(400, f"Ce signalement a déjà été traité (statut: {signalement.statut}).")
    
    if not data.motif_rejet or not data.motif_rejet.strip():
        raise HttpError(400, "Le motif de rejet est obligatoire.")
    
    # Mettre à jour le signalement
    signalement.statut = 'rejete'
    signalement.valide_par = request.auth
    signalement.motif_rejet = data.motif_rejet
    signalement.date_validation = timezone.now()
    signalement.save()
    
    # Journal d'audit
    log_action(
        request.auth,
        "update",
        "CaveauSignalement",
        signalement.id,
        f"Signalement rejeté pour caveau {signalement.grave.code}. Motif: {data.motif_rejet}"
    )
    
    return signalement


@router.post("/graves/{grave_id}/declarer-non-exploitable/")
@require_role("admin")
def declarer_non_exploitable_direct(request, grave_id: int):
    """
    L'administrateur déclare directement un caveau non exploitable (sans passer par un signalement).
    Utile quand l'admin constate lui-même le problème.
    """
    grave = get_object_or_404(Grave, id=grave_id)
    
    if grave.status == 'non_exploitable':
        raise HttpError(400, "Ce caveau est déjà non exploitable.")
    
    # Récupérer le motif depuis le body de la requête
    import json
    try:
        body = json.loads(request.body)
        motif = body.get("motif", "")
    except:
        motif = ""
    
    if not motif:
        raise HttpError(400, "Le motif est obligatoire.")
    
    # Mettre à jour le caveau
    grave.status = 'non_exploitable'
    grave.motif_non_exploitable = motif
    grave.date_non_exploitable = timezone.now()
    grave.non_exploitable_par = request.auth
    grave.last_status_change = timezone.now()
    grave.save()
    
    # Journal d'audit
    log_action(
        request.auth,
        "status_change",
        "Grave",
        grave.id,
        f"Caveau {grave.code} déclaré non exploitable directement par l'admin. Motif: {motif}"
    )
    
    return {"message": f"Caveau {grave.code} déclaré non exploitable avec succès."}


@router.post("/graves/{grave_id}/remettre-en-exploitation/")
@require_role("admin")
def remettre_en_exploitation(request, grave_id: int):
    """
    L'administrateur remet un caveau en exploitation après réparation.
    Le statut redevient 'available' (ou peut être personnalisé).
    """
    grave = get_object_or_404(Grave, id=grave_id)
    
    if grave.status != 'non_exploitable':
        raise HttpError(400, f"Ce caveau n'est pas non exploitable (statut actuel: {grave.status}).")
    
    # Récupérer le nouveau statut depuis le body (optionnel, défaut: available)
    import json
    try:
        body = json.loads(request.body)
        nouveau_statut = body.get("nouveau_statut", "available")
    except:
        nouveau_statut = "available"
    
    if nouveau_statut not in ['available', 'reserved', 'occupied']:
        raise HttpError(400, "Statut invalide. Valeurs acceptées: available, reserved, occupied.")
    
    # Mettre à jour le caveau
    ancien_statut = grave.status
    grave.status = nouveau_statut
    grave.motif_non_exploitable = ""
    grave.date_non_exploitable = None
    grave.non_exploitable_par = None
    grave.last_status_change = timezone.now()
    grave.save()
    
    # Journal d'audit
    log_action(
        request.auth,
        "status_change",
        "Grave",
        grave.id,
        f"Caveau {grave.code} remis en exploitation. Ancien statut: {ancien_statut}, Nouveau statut: {nouveau_statut}"
    )
    
    return {"message": f"Caveau {grave.code} remis en exploitation avec succès."}