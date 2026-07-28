"""
projet_cimetiere/cemeterre_backend/cemetery/api_concessions.py
API complète pour la gestion des concessions.
CORRECTION DÉFINITIVE : Réorganisation des routes pour placer les routes statiques 
AVANT les routes dynamiques ({concession_id}), évitant ainsi les erreurs 405.
"""

from ninja import Router
from django.utils import timezone
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum, Q
from datetime import timedelta, date
import json

from .models import Concession, ConcessionRenewal, Grave
from .schemas import (
    ConcessionIn, ConcessionOut, ConcessionRenewalIn, ConcessionRenewalOut,
    ConcessionStatsSchema, ConcessionCreateFromReservationIn
)
from users.models import User
from finance.models import Facture
from reservations.models import Reservation
from core.permissions import require_role
from core.audit import log_action
from .pdf_utils import generate_concession_contrat_pdf
from .emails import send_concession_contrat_email, send_expiration_alert_email

# ✅ Imports pour les notifications
from notifications.utils_extended import notifier_concession_creee
from cemetery.emails_extended import send_concession_created_email


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


router = Router(auth=JWTAuth(), tags=["Concessions"])


# ==============================================================================
# 1. ROUTES STATIQUES (SANS PARAMÈTRE {concession_id})
# ⚠️ DOIVENT ABSOLUMENT ÊTRE PLACÉES EN PREMIER
# ==============================================================================

@router.get("/concessions", response=list[ConcessionOut])
@require_role("admin", "secretariat")
def list_concessions(request, status: str = None, type_concession: str = None, search: str = None):
    queryset = Concession.objects.all().select_related("grave", "user", "grave__section")
    if status:
        queryset = queryset.filter(status=status)
    if type_concession:
        queryset = queryset.filter(type_concession=type_concession)
    if search:
        queryset = queryset.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(grave__code__icontains=search)
        )
    return queryset.order_by("-created_at")


@router.post("/concessions", response=ConcessionOut)
@require_role("admin")
def create_concession(request, data: ConcessionIn):
    """Création manuelle d'une concession (admin uniquement, cas exceptionnel)"""
    grave = get_object_or_404(Grave, id=data.grave_id)
    user = get_object_or_404(User, id=data.user_id)

    if hasattr(grave, 'concession') and grave.concession.status == 'active':
        raise HttpError(400, "Ce caveau possède déjà une concession active")

    concession = Concession.objects.create(
        grave=grave,
        user=user,
        type_concession=data.type_concession,
        montant=data.montant,
        date_debut=data.date_debut,
        duree_annees=data.duree_annees if data.type_concession == 'temporaire' else None,
        date_fin=data.date_fin,
        is_paid=True,
        status="active"
    )

    grave.status = "reserved"
    grave.last_status_change = timezone.now()
    grave.save()

    try:
        pdf_bytes = generate_concession_contrat_pdf(concession)
        filename = f"contrat_{concession.id}.pdf"
        from django.core.files.base import ContentFile
        concession.contrat_document.save(filename, ContentFile(pdf_bytes))
        concession.save()
    except Exception as e:
        print(f"⚠️ Erreur génération PDF contrat: {e}")

    try:
        notifier_concession_creee(concession)
        send_concession_created_email(concession)
    except Exception as e:
        print(f"⚠️ Erreur notification concession créée : {e}")

    log_action(request.auth, "create", "Concession", concession.id, f"Création manuelle - {grave.code}")
    return concession


@router.get("/concessions/expiring", response=list[ConcessionOut])
@require_role("admin", "secretariat")
def concessions_expiring_soon(request, days: int = 90):
    """Liste les concessions expirant dans les prochains jours (défaut 90 jours)"""
    today = timezone.now().date()
    threshold = today + timedelta(days=days)
    return Concession.objects.filter(
        status="active",
        type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
        date_fin__lte=threshold,
        date_fin__gte=today
    ).select_related("grave", "user", "grave__section")


@router.get("/concessions/ready-for-creation", response=list[dict])
@require_role("admin", "secretariat")
def concessions_ready_for_creation(request):
    """Liste les réservations confirmées avec facture payée, prêtes pour création manuelle."""
    reservations = Reservation.objects.filter(
        status="confirmed"
    ).select_related("user", "grave", "grave__section")
    
    result = []
    for res in reservations:
        if hasattr(res.grave, 'concession') and res.grave.concession.status == 'active':
            continue
            
        facture = Facture.objects.filter(reservation=res, statut="payee").first()
        if facture:
            result.append({
                "reservation_id": res.id,
                "grave_code": res.grave.code,
                "client_username": res.user.username,
                "client_email": res.user.email,
                "montant": float(facture.montant_total),
                "date_reservation": res.reservation_date.isoformat() if res.reservation_date else "",
            })
    
    return result


@router.get("/concessions/stats", response=ConcessionStatsSchema)
@require_role("admin", "secretariat")
def concessions_stats(request):
    """Statistiques des concessions alignées avec ConcessionStatsSchema."""
    today = timezone.now().date()
    
    total = Concession.objects.count()
    actives = Concession.objects.filter(status="active").count()
    expired = Concession.objects.filter(status="expired").count()
    resiliees = Concession.objects.filter(status="resiliee").count()
    temporaires = Concession.objects.filter(type_concession="temporaire").count()
    perpetuelles = Concession.objects.filter(type_concession="perpetuelle").count()
    
    # ✅ CORRECTION : Calculer les concessions expirant dans 15 jours (pour correspondre au schéma)
    expiring_15 = Concession.objects.filter(
        status="active",
        type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
        date_fin__lte=today + timedelta(days=15),
        date_fin__gte=today
    ).count()
    
    revenus = Concession.objects.filter(
        is_paid=True,
        status__in=["active", "expired"]
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    concessions_avec_renewal = Concession.objects.filter(renewed_count__gt=0).count()
    taux_renouvellement = (concessions_avec_renewal / total * 100) if total > 0 else 0
    
    # ✅ CORRECTION : Retourner exactement les champs définis dans ConcessionStatsSchema
    return {
        "total": total,
        "actives": actives,
        "expired": expired,
        "resiliees": resiliees,
        "temporaires": temporaires,
        "perpetuelles": perpetuelles,
        "expiring_in_15_days": expiring_15,
        "revenus_total": float(revenus),
        "taux_renouvellement": round(taux_renouvellement, 2)
    }


@router.post("/concessions/from-reservation", response=ConcessionOut)
@require_role("admin", "secretariat")
def create_concession_from_reservation(request, data: ConcessionCreateFromReservationIn):
    """Crée une concession depuis une réservation validée et payée."""
    reservation = get_object_or_404(
        Reservation.objects.select_related("user", "grave"),
        id=data.reservation_id
    )
    
    if reservation.status != "confirmed":
        raise HttpError(400, "La réservation doit être confirmée.")
    
    facture = Facture.objects.filter(reservation=reservation, statut="payee").first()
    if not facture:
        raise HttpError(400, "La facture associée à cette réservation doit être entièrement payée.")
    
    if hasattr(reservation.grave, 'concession') and reservation.grave.concession.status == 'active':
        raise HttpError(400, "Ce caveau possède déjà une concession active.")
    
    concession = Concession.objects.create(
        grave=reservation.grave,
        user=reservation.user,
        type_concession=data.type_concession,
        montant=reservation.grave.price,
        date_debut=timezone.now().date(),
        duree_annees=data.duree_annees if data.type_concession == 'temporaire' else None,
        is_paid=True,
        status="active"
    )
    
    reservation.grave.status = "reserved"
    reservation.grave.last_status_change = timezone.now()
    reservation.grave.save()
    
    try:
        pdf_bytes = generate_concession_contrat_pdf(concession)
        filename = f"contrat_{concession.id}.pdf"
        from django.core.files.base import ContentFile
        concession.contrat_document.save(filename, ContentFile(pdf_bytes))
        concession.save()
    except Exception as e:
        print(f"⚠️ Erreur génération PDF contrat: {e}")
    
    try:
        send_concession_contrat_email(concession, facture, is_renewal=False)
    except Exception as e:
        print(f"⚠️ Erreur email contrat: {e}")
        
    try:
        notifier_concession_creee(concession)
        send_concession_created_email(concession)
    except Exception as e:
        print(f"⚠️ Erreur notification concession créée : {e}")
    
    log_action(
        request.auth, "create", "Concession", concession.id, 
        f"Créée depuis réservation {reservation.id} - Type: {data.type_concession}"
    )
    
    return concession


@router.post("/concessions/check-expirations")
@require_role("admin", "secretariat")
def check_expirations_task(request):
    """Vérifie les concessions arrivant à échéance et envoie des alertes."""
    today = timezone.now().date()
    results = {"emails_sent": 0, "expired": 0, "notified_90": 0, "notified_30": 0}
    
    concessions_90 = Concession.objects.filter(
        status="active",
        type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
        date_fin__lte=today + timedelta(days=90),
        date_fin__gt=today + timedelta(days=89)
    ).select_related("user", "grave")
    
    for c in concessions_90:
        if c.user.email:
            try:
                send_expiration_alert_email(c, days=90)
                results["notified_90"] += 1
            except Exception as e:
                print(f"⚠️ Erreur email J-90 pour {c.id}: {e}")
    
    concessions_30 = Concession.objects.filter(
        status="active",
        type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
        date_fin__lte=today + timedelta(days=30),
        date_fin__gt=today + timedelta(days=29)
    ).select_related("user", "grave")
    
    for c in concessions_30:
        if c.user.email:
            try:
                send_expiration_alert_email(c, days=30)
                results["notified_30"] += 1
            except Exception as e:
                print(f"⚠️ Erreur email J-30 pour {c.id}: {e}")
    
    expired_concessions = Concession.objects.filter(
        status="active",
        type_concession__in=['temporaire', 'trentenaire', 'cinquantenaire'],
        date_fin__lt=today
    )
    results["expired"] = expired_concessions.update(status="expired")
    
    return {"message": "Vérification terminée", "details": results}


# ==============================================================================
# 2. ROUTES DYNAMIQUES (AVEC PARAMÈTRE {concession_id})
# ⚠️ DOIVENT ABSOLUMENT ÊTRE PLACÉES APRÈS LES ROUTES STATIQUES
# ==============================================================================

@router.get("/concessions/{concession_id}", response=ConcessionOut)
@require_role("admin", "secretariat", "client")
def get_concession(request, concession_id: int):
    concession = get_object_or_404(
        Concession.objects.select_related("grave", "user", "grave__section"),
        id=concession_id
    )
    if request.auth.role == "client" and concession.user_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")
    return concession


@router.get("/concessions/{concession_id}/historique", response=list[ConcessionRenewalOut])
@require_role("admin", "secretariat", "client")
def get_concession_historique(request, concession_id: int):
    concession = get_object_or_404(Concession, id=concession_id)
    if request.auth.role == "client" and concession.user_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")
    return ConcessionRenewal.objects.filter(concession=concession).select_related("renewed_by")


@router.put("/concessions/{concession_id}/renew", response=ConcessionOut)
@require_role("admin", "secretariat")
def renew_concession(request, concession_id: int, data: ConcessionRenewalIn):
    """Renouvelle une concession existante"""
    concession = get_object_or_404(Concession, id=concession_id)

    if concession.type_concession == 'perpetuelle':
        raise HttpError(400, "Une concession perpétuelle ne peut pas être renouvelée.")
    if concession.status != 'active':
        raise HttpError(400, "Seule une concession active peut être renouvelée.")

    base_date = concession.date_fin if concession.date_fin else timezone.now().date()
    ancienne_date_fin = base_date
    
    if data.type_concession == 'trentenaire':
        nouvelle_date_fin = base_date + timedelta(days=30 * 365)
        duree = 30
    elif data.type_concession == 'cinquantenaire':
        nouvelle_date_fin = base_date + timedelta(days=50 * 365)
        duree = 50
    else:
        nouvelle_date_fin = base_date + timedelta(days=data.duree_annees * 365)
        duree = data.duree_annees
    
    montant_renouvellement = data.montant if data.montant else concession.montant

    facture = Facture.objects.create(
        client=concession.user,
        numero=f"REN-{timezone.now().year}-{concession.renewed_count + 1:04d}",
        montant_total=montant_renouvellement,
        date_echeance=timezone.now().date() + timedelta(days=30),
        statut="en_attente",
    )

    ConcessionRenewal.objects.create(
        concession=concession,
        ancienne_date_fin=ancienne_date_fin,
        nouvelle_date_fin=nouvelle_date_fin,
        duree_extension_annees=duree,
        montant_paye=montant_renouvellement,
        facture=facture,
        renewed_by=request.auth,
        observations=f"Renouvellement {data.type_concession} - {duree} ans"
    )

    concession.type_concession = data.type_concession
    concession.date_fin = nouvelle_date_fin
    concession.duree_annees = duree if data.type_concession == 'temporaire' else None
    concession.renewed_count += 1
    concession.last_renewal_at = timezone.now()
    concession.save()

    try:
        pdf_bytes = generate_concession_contrat_pdf(concession)
        from django.core.files.base import ContentFile
        concession.contrat_document.save(f"contrat_{concession.id}_v{concession.renewed_count}.pdf", ContentFile(pdf_bytes))
    except Exception as e:
        print(f"⚠️ Erreur PDF renouvellement: {e}")

    try:
        send_concession_contrat_email(concession, facture, is_renewal=True)
    except Exception as e:
        print(f"⚠️ Erreur email renouvellement: {e}")

    log_action(request.auth, "update", "Concession", concession.id, 
               f"Renouvellement {data.type_concession} {duree} ans - Nouvelle fin: {nouvelle_date_fin}")

    return concession


@router.put("/concessions/{concession_id}/resilier")
@require_role("admin")
def resilier_concession(request, concession_id: int):
    """Résiliation d'une concession (admin uniquement, avec motif)"""
    concession = get_object_or_404(Concession, id=concession_id)
    if concession.status == 'resiliee':
        raise HttpError(400, "Cette concession est déjà résiliée.")

    try:
        body = json.loads(request.body)
        motif = body.get("motif", "")
    except:
        motif = ""

    if not motif:
        raise HttpError(400, "Le motif de résiliation est obligatoire.")

    concession.status = "resiliee"
    concession.save()

    grave = concession.grave
    grave.status = "available"
    grave.last_status_change = timezone.now()
    grave.save()

    log_action(request.auth, "status_change", "Concession", concession.id, f"Résiliation - Motif: {motif}")
    return {"message": "Concession résiliée, caveau libéré"}


@router.delete("/concessions/{concession_id}")
@require_role("admin")
def delete_concession(request, concession_id: int):
    """Suppression administrative d'une concession"""
    concession = get_object_or_404(Concession, id=concession_id)
    if concession.status == 'active':
        grave = concession.grave
        grave.status = "available"
        grave.save()
    
    concession_id_saved = concession.id
    concession.delete()
    log_action(request.auth, "delete", "Concession", concession_id_saved, "Suppression administrative")
    return {"message": "Concession supprimée"}


@router.get("/concessions/{concession_id}/contrat/download", auth=jwt_auth_or_query_param)
@require_role("admin", "secretariat", "client")
def download_contrat_pdf(request, concession_id: int):
    """Télécharger le contrat de concession en PDF (modèle juridique)."""
    concession = get_object_or_404(
        Concession.objects.select_related("grave", "user", "grave__section"),
        id=concession_id
    )
    if request.auth.role == "client" and concession.user_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")

    pdf_bytes = generate_concession_contrat_pdf(concession)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="Contrat_Concession_{concession.id:06d}.pdf"'
    return response


@router.post("/concessions/{concession_id}/send-contrat")
@require_role("admin", "secretariat")
def send_contrat_email(request, concession_id: int):
    """Renvoyer le contrat par email"""
    concession = get_object_or_404(Concession, id=concession_id)
    if not concession.user.email:
        raise HttpError(400, "Le client n'a pas d'email enregistré.")
    
    try:
        send_concession_contrat_email(concession, facture=None, is_renewal=False)
        log_action(request.auth, "update", "Concession", concession.id, "Contrat renvoyé par email")
        return {"message": "Contrat envoyé par email avec succès."}
    except Exception as e:
        raise HttpError(500, f"Erreur d'envoi : {str(e)}")