# projet_cimetiere/cemeterre_backend/finance/api.py

from ninja import Router
from ninja_jwt.authentication import JWTAuth
from ninja.errors import HttpError
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Max
from datetime import timedelta
import uuid

from .models import Facture, Paiement
from .schemas import (
    FactureCreateSchema, FactureSchema, 
    PaiementEspecesSchema, PaiementMobileSchema, PaiementVirementSchema,
    PaiementHistoriqueSchema, StatsFinanceSchema
)
from .validators import validate_mtn_number, validate_airtel_number, validate_montant_paiement
from reservations.models import Reservation
from core.permissions import require_role
from .mtn_momo import MTNMoMoAPI
from .airtel_money import AirtelMoneyAPI
from .pdf_utils import generate_facture_pdf
from notifications.utils_extended import notifier_paiement_recu
from cemetery.emails_extended import send_payment_confirmation_email

router = Router(auth=JWTAuth(), tags=["Finance"])
mtn_client = MTNMoMoAPI()
airtel_client = AirtelMoneyAPI()


def generate_facture_numero() -> str:
    annee = timezone.now().year
    last_facture = Facture.objects.filter(numero__startswith=f"FACT-{annee}-").aggregate(Max('numero'))
    last_numero = last_facture['numero__max']
    nouveau_chiffre = (int(last_numero.split('-')[-1]) + 1) if last_numero else 1
    return f"FACT-{annee}-{nouveau_chiffre:04d}"


def _check_facture_pour_paiement(facture_id: int, user):
    """Vérifications communes avant tout paiement"""
    facture = get_object_or_404(Facture, id=facture_id)
    if facture.statut == 'annulee':
        raise HttpError(400, "Cette facture a été annulée.")
    if facture.is_paid:
        raise HttpError(400, "Cette facture est déjà entièrement payée.")
    if user.role == "client" and facture.client_id != user.id:
        raise HttpError(403, "Accès refusé à cette facture.")
    return facture


def _facture_to_dict(facture):
    """Convertit une facture en dictionnaire avec toutes les données nécessaires."""
    return {
        "id": facture.id,
        "numero": facture.numero,
        "montant_total": float(facture.montant_total),
        "montant_paye": float(facture.montant_paye),
        "montant_restant": float(facture.montant_restant),
        "statut": facture.statut,
        "is_paid": facture.is_paid,
        "date_echeance": facture.date_echeance.isoformat() if facture.date_echeance else None,
        "reservation_id": facture.reservation_id,
        "client_id": facture.client_id,
        "client_username": facture.client.username if facture.client else "Inconnu",
        "client_email": facture.client.email if facture.client else "",
        "created_at": facture.created_at.isoformat() if facture.created_at else None,
    }


# ==============================================================================
# 1. LISTE DES FACTURES (Routes statiques - DOIVENT ÊTRE EN PREMIER)
# ==============================================================================
@router.get("/factures/mine")
@require_role("admin", "secretariat", "agent", "client")
def list_my_factures(request):
    """Liste les factures du client connecté avec données enrichies."""
    factures = Facture.objects.filter(
        client=request.auth
    ).select_related("client", "reservation").order_by("-created_at")
    
    return [_facture_to_dict(f) for f in factures]


@router.get("/factures")
@require_role("admin", "secretariat")
def list_factures(request, statut: str = None):
    """Liste toutes les factures avec données enrichies."""
    queryset = Facture.objects.all().select_related("client", "reservation")
    if statut:
        queryset = queryset.filter(statut=statut)
    factures = queryset.order_by("-created_at")
    
    return [_facture_to_dict(f) for f in factures]


# ==============================================================================
# 2. DÉTAIL D'UNE FACTURE (Route dynamique - APRÈS les routes statiques)
# ==============================================================================
@router.get("/factures/{facture_id}")
@require_role("admin", "secretariat", "client")
def get_facture(request, facture_id: int):
    """Récupère les détails d'une facture spécifique"""
    facture = get_object_or_404(Facture, id=facture_id)
    if request.auth.role == "client" and facture.client_id != request.auth.id:
        raise HttpError(403, "Vous n'avez pas accès à cette facture.")
    return _facture_to_dict(facture)


# ==============================================================================
# 3. CRÉATION DE FACTURE
# ==============================================================================
@router.post("/factures", response=FactureSchema)
@require_role("admin", "secretariat")
def creer_facture(request, data: FactureCreateSchema):
    reservation = get_object_or_404(Reservation, id=data.reservation_id)
    if hasattr(reservation, "facture"):
        raise HttpError(400, "Une facture existe déjà pour cette réservation")

    return Facture.objects.create(
        reservation=reservation,
        client=reservation.user,
        numero=generate_facture_numero(),
        montant_total=data.montant_total,
        date_echeance=data.date_echeance or (timezone.now().date() + timedelta(days=30)),
        statut="en_attente"
    )


# ==============================================================================
# 4. PAIEMENTS MULTI-CANAUX
# ==============================================================================
@router.post("/factures/{facture_id}/paiement/especes/", response=FactureSchema)
@require_role("admin", "secretariat")
def payer_especes(request, facture_id: int, data: PaiementEspecesSchema):
    print(f" [API] Paiement espèces pour facture {facture_id}, montant: {data.montant}")
    facture = _check_facture_pour_paiement(facture_id, request.auth)
    validate_montant_paiement(float(data.montant), facture.montant_restant)

    Paiement.objects.create(
        facture=facture,
        montant=data.montant,
        mode_paiement='especes',
        reference=data.reference or f"ESP-{uuid.uuid4().hex[:6].upper()}",
        traite_par=request.auth,
        statut_validation='valide'
    )
    
    facture.refresh_from_db()
    print(f"✅ [API] Paiement espèces enregistré. Nouveau statut: {facture.statut}")
    
    if facture.is_paid:
        try:
            notifier_paiement_recu(facture)
            send_payment_confirmation_email(facture)
        except Exception as e:
            print(f"⚠️ [API] Erreur notification/email: {e}")
        
    return facture


@router.post("/factures/{facture_id}/paiement/mtn/", response=FactureSchema)
@require_role("admin", "secretariat", "client")
def payer_mtn(request, facture_id: int, data: PaiementMobileSchema):
    print(f" [API] Paiement MTN pour facture {facture_id}, téléphone: {data.phone}, montant: {data.montant}")
    facture = _check_facture_pour_paiement(facture_id, request.auth)
    validate_montant_paiement(float(data.montant), facture.montant_restant)
    
    try:
        clean_phone = validate_mtn_number(data.phone)
    except Exception as e:
        print(f"❌ [API] Validation numéro MTN échouée: {e}")
        raise HttpError(400, str(e))

    reference = f"MTN-{uuid.uuid4().hex[:6].upper()}"
    print(f" [API] Appel API MTN avec référence: {reference}")
    response_api = mtn_client.request_to_pay(amount=float(data.montant), phone=clean_phone, reference=reference)
    print(f" [API] Réponse MTN: {response_api}")
    
    if response_api.get("status") != "success":
        print(f"❌ [API] Échec MTN: {response_api.get('message')}")
        raise HttpError(400, f"Échec MTN : {response_api.get('message')}")

    Paiement.objects.create(
        facture=facture,
        montant=data.montant,
        mode_paiement='mtn_momo',
        reference=response_api.get("reference_id") or reference,
        traite_par=request.auth,
        statut_validation='valide'
    )
    
    facture.refresh_from_db()
    print(f"✅ [API] Paiement MTN enregistré. Nouveau statut: {facture.statut}")
    
    if facture.is_paid:
        try:
            notifier_paiement_recu(facture)
            send_payment_confirmation_email(facture)
        except Exception as e:
            print(f"⚠️ [API] Erreur notification/email: {e}")
        
    return facture


@router.post("/factures/{facture_id}/paiement/airtel/", response=FactureSchema)
@require_role("admin", "secretariat", "client")
def payer_airtel(request, facture_id: int, data: PaiementMobileSchema):
    print(f"🔵 [API] Paiement Airtel pour facture {facture_id}, téléphone: {data.phone}, montant: {data.montant}")
    facture = _check_facture_pour_paiement(facture_id, request.auth)
    validate_montant_paiement(float(data.montant), facture.montant_restant)
    
    try:
        clean_phone = validate_airtel_number(data.phone)
    except Exception as e:
        print(f" [API] Validation numéro Airtel échouée: {e}")
        raise HttpError(400, str(e))

    reference = f"AIRTEL-{uuid.uuid4().hex[:6].upper()}"
    print(f"📱 [API] Appel API Airtel avec référence: {reference}")
    response_api = airtel_client.make_payment(amount=float(data.montant), phone=clean_phone, reference=reference)
    print(f"📱 [API] Réponse Airtel: {response_api}")
    
    if response_api.get("status") != "success":
        print(f"❌ [API] Échec Airtel: {response_api.get('message')}")
        raise HttpError(400, f"Échec Airtel : {response_api.get('message')}")

    Paiement.objects.create(
        facture=facture,
        montant=data.montant,
        mode_paiement='airtel_money',
        reference=response_api.get("transaction_id") or reference,
        traite_par=request.auth,
        statut_validation='valide'
    )
    
    facture.refresh_from_db()
    print(f"✅ [API] Paiement Airtel enregistré. Nouveau statut: {facture.statut}")
    
    if facture.is_paid:
        try:
            notifier_paiement_recu(facture)
            send_payment_confirmation_email(facture)
        except Exception as e:
            print(f"⚠️ [API] Erreur notification/email: {e}")
        
    return facture


@router.post("/factures/{facture_id}/paiement/virement/", response=FactureSchema)
@require_role("admin", "secretariat", "client")
def payer_virement(request, facture_id: int, data: PaiementVirementSchema):
    print(f"🔵 [API] Paiement virement pour facture {facture_id}, référence: {data.reference_virement}, montant: {data.montant}")
    facture = _check_facture_pour_paiement(facture_id, request.auth)
    validate_montant_paiement(float(data.montant), facture.montant_restant)

    paiement = Paiement.objects.create(
        facture=facture,
        montant=data.montant,
        mode_paiement='virement',
        reference=data.reference_virement,
        statut_validation='en_attente',
        traite_par=request.auth
    )
    
    facture.refresh_from_db()
    print(f"✅ [API] Paiement virement enregistré (en attente). ID: {paiement.id}")
    
    return {
        "id": facture.id,
        "numero": facture.numero,
        "montant_total": facture.montant_total,
        "montant_paye": facture.montant_paye,
        "montant_restant": facture.montant_restant,
        "statut": facture.statut,
        "is_paid": facture.is_paid,
        "date_echeance": facture.date_echeance,
        "reservation_id": facture.reservation_id,
        "client_id": facture.client_id,
        "created_at": facture.created_at,
        "client_username": facture.client.username,
        "client_email": facture.client.email,
        "progression": facture.progression,
        "message_virement": "Virement enregistré. En attente de validation par l'administration."
    }


@router.post("/paiements/{paiement_id}/confirmer/", response=FactureSchema)
@require_role("admin", "secretariat")
def confirmer_virement(request, paiement_id: int):
    print(f" [API] Confirmation virement pour paiement {paiement_id}")
    paiement = get_object_or_404(Paiement, id=paiement_id, mode_paiement='virement')
    
    if paiement.statut_validation != 'en_attente':
        raise HttpError(400, "Ce paiement est déjà traité.")
        
    paiement.statut_validation = 'valide'
    paiement.save()
    
    facture = paiement.facture
    print(f"✅ [API] Virement confirmé. Nouveau statut facture: {facture.statut}")
    
    if facture.is_paid:
        try:
            notifier_paiement_recu(facture)
            send_payment_confirmation_email(facture)
        except Exception as e:
            print(f"⚠️ [API] Erreur notification/email: {e}")
        
    return facture


# ==============================================================================
# 5. HISTORIQUE ET TÉLÉCHARGEMENT
# ==============================================================================
@router.get("/factures/{facture_id}/historique/", response=list[PaiementHistoriqueSchema])
@require_role("admin", "secretariat", "client")
def get_historique_facture(request, facture_id: int):
    facture = get_object_or_404(Facture, id=facture_id)
    if request.auth.role == "client" and facture.client_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")
    
    return facture.paiements.all().order_by("-date_paiement")


@router.get("/factures/{facture_id}/pdf")
@require_role("admin", "secretariat", "client")
def download_facture_pdf(request, facture_id: int):
    facture = get_object_or_404(Facture, id=facture_id)
    if request.auth.role == "client" and facture.client_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")

    pdf_bytes = generate_facture_pdf(facture)
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{facture.numero}.pdf"'
    return response


# ==============================================================================
# 6. STATISTIQUES
# ==============================================================================
@router.get("/stats", response=StatsFinanceSchema)
@require_role("admin")
def stats_finance(request):
    factures = list(Facture.objects.all())
    total_attendu = sum(float(f.montant_total or 0) for f in factures)
    total_paye = sum(float(f.montant_paye or 0) for f in factures)
    
    return {
        "total_factures": len(factures),
        "total_attendu": total_attendu,
        "total_paye": total_paye,
        "total_restant": total_attendu - total_paye,
        "payees": len([f for f in factures if f.statut == "payee"]),
        "en_attente": len([f for f in factures if f.statut == "en_attente"]),
        "partielles": len([f for f in factures if f.statut == "partielle"]),
    }


# ==============================================================================
# 7. GESTION DES VIREMENTS EN ATTENTE (Pour l'Admin)
# ==============================================================================
@router.get("/paiements/virements-en-attente")
@require_role("admin", "secretariat")
def get_virements_en_attente(request):
    """Récupère tous les virements qui attendent une validation manuelle."""
    paiements = Paiement.objects.filter(
        mode_paiement='virement',
        statut_validation='en_attente'
    ).select_related("facture__client").order_by("-date_paiement")
    
    result = []
    for p in paiements:
        result.append({
            "id": p.id,
            "facture_id": p.facture_id,
            "facture_numero": p.facture.numero if p.facture else None,
            "montant": float(p.montant),
            "mode_paiement": p.mode_paiement,
            "reference": p.reference,
            "statut_validation": p.statut_validation,
            "date_paiement": p.date_paiement.isoformat() if p.date_paiement else None,
            "client_username": p.facture.client.username if p.facture and p.facture.client else "Inconnu",
            "client_email": p.facture.client.email if p.facture and p.facture.client else "",
        })
    return result


@router.post("/paiements/{paiement_id}/valider-virement", response=FactureSchema)
@require_role("admin", "secretariat")
def valider_virement_admin(request, paiement_id: int):
    """L'admin clique ici pour valider qu'il a bien reçu l'argent sur le compte bancaire."""
    paiement = get_object_or_404(Paiement, id=paiement_id, mode_paiement='virement')
    
    if paiement.statut_validation != 'en_attente':
        raise HttpError(400, "Ce virement a déjà été traité.")
        
    paiement.statut_validation = 'valide'
    paiement.save()
    
    facture = paiement.facture
    if facture.is_paid:
        try:
            from notifications.utils_extended import notifier_paiement_recu
            from cemetery.emails_extended import send_payment_confirmation_email
            notifier_paiement_recu(facture)
            send_payment_confirmation_email(facture)
        except Exception:
            pass
        
    return facture