"""
projet_cimetiere/cemeterre_backend/reservations/api.py
Routeurs Django Ninja pour les réservations.
CORRECTION : Utilisation de ReservationSchema (qui existe) au lieu de ReservationOut.
"""
from ninja import Router, Schema
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from datetime import date, datetime, time

from .models import Reservation
# ✅ CORRECTION : Suppression de ReservationOut, on utilise ReservationSchema
from .schemas import ReservationCreateSchema, ReservationStatusSchema, ReservationSchema
from cemetery.models import Grave, Inhumation
from finance.models import Facture
from users.models import User
from core.permissions import require_role
from notifications.utils import (
    notifier_nouvelle_reservation,
    notifier_reservation_validee,
    notifier_reservation_annulee,
)
from notifications.utils_extended import (
    notifier_reservation_validee_avec_facture,
    notifier_inhumation_confirmee
)
from cemetery.emails_extended import send_reservation_validated_email

router = Router(auth=JWTAuth(), tags=["Reservations"])


# ==============================================================================
# SCHÉMAS POUR CONFIRMER INHUMATION
# ==============================================================================
class ConfirmerInhumationIn(Schema):
    date_inhumation: date
    heure_inhumation: str | None = None
    observations: str | None = None


class ConfirmerInhumationOut(Schema):
    reservation_id: int
    inhumation_id: int
    grave_status: str
    reservation_status: str
    message: str
    is_anticipée: bool = False


# ==============================================================================
# ROUTES STATIQUES (AVANT les routes dynamiques)
# ==============================================================================

@router.post("/manual/", response=dict)
@require_role("admin", "secretariat", "client")
def create_reservation_manual(request, data: ReservationCreateSchema):
    grave = get_object_or_404(Grave, id=data.grave_id)
    if grave.status != "available":
        raise HttpError(400, "Ce caveau n'est pas disponible.")

    if data.user_id:
        user = get_object_or_404(User, id=data.user_id)
    else:
        user = request.auth

    reservation = Reservation.objects.create(
        user=user,
        grave=grave,
        deceased_first_name=data.deceased_first_name or "",
        deceased_last_name=data.deceased_last_name or "",
        deceased_birth_date=data.deceased_birth_date,
        deceased_death_date=data.deceased_death_date,
        note=data.note or "",
        date_prevue_inhumation=data.date_prevue_inhumation,
        status="pending"
    )

    try:
        notifier_nouvelle_reservation(reservation)
    except Exception as e:
        print(f"⚠️ Erreur notification : {e}")

    return {"id": reservation.id, "message": "Réservation créée avec succès."}


@router.get("/mine", response=list[ReservationSchema])
@require_role("client", "admin", "secretariat")
def list_my_reservations(request):
    """Liste les réservations du client connecté."""
    return Reservation.objects.filter(
        user=request.auth
    ).select_related("grave", "grave__section").order_by("-reservation_date")


@router.get("/", response=list[ReservationSchema])
@require_role("admin", "secretariat", "agent")
def list_reservations(request, status: str = None):
    qs = Reservation.objects.select_related("user", "grave__section").all()
    if status:
        qs = qs.filter(status=status)
    return qs


@router.post("/", response=dict)
@require_role("admin", "agent", "client")
def create_reservation(request, data: ReservationCreateSchema):
    if request.auth.role == "client":
        target_user = request.auth
    else:
        target_user_id = data.user_id if data.user_id else request.auth.id
        target_user = get_object_or_404(User, id=target_user_id)

    grave = get_object_or_404(Grave, id=data.grave_id)
    if grave.status != "available":
        raise HttpError(400, "Ce caveau n'est pas disponible.")

    reservation = Reservation.objects.create(
        user=target_user,
        grave=grave,
        note=data.note or "",
        deceased_first_name=data.deceased_first_name or "",
        deceased_last_name=data.deceased_last_name or "",
        deceased_birth_date=data.deceased_birth_date,
        deceased_death_date=data.deceased_death_date,
        date_prevue_inhumation=data.date_prevue_inhumation,
        status="pending"
    )

    try:
        notifier_nouvelle_reservation(reservation)
    except Exception as e:
        print(f"⚠️ Erreur notification : {e}")

    return {"id": reservation.id, "message": "Réservation créée."}


# ==============================================================================
# ROUTES DYNAMIQUES (APRÈS les routes statiques)
# ==============================================================================

@router.get("/{reservation_id}/", response=ReservationSchema)
@require_role("admin", "secretariat", "agent", "client")
def get_reservation(request, reservation_id: int):
    res = get_object_or_404(
        Reservation.objects.select_related("user", "grave__section"), 
        id=reservation_id
    )
    # ✅ Sécurité : un client ne peut voir que sa propre réservation
    if request.auth.role == "client" and res.user_id != request.auth.id:
        raise HttpError(403, "Accès refusé.")
    return res


@router.put("/{reservation_id}/", response=dict)
@require_role("admin", "secretariat")
def update_reservation_status(request, reservation_id: int, data: ReservationStatusSchema):
    reservation = get_object_or_404(Reservation, id=reservation_id)
    reservation.status = data.status
    if data.note_validation:
        reservation.note = f"{reservation.note}\n[Validation]: {data.note_validation}" if reservation.note else data.note_validation
    
    reservation.save()

    if data.status == "confirmed":
        from datetime import timedelta
        montant = reservation.grave.price if reservation.grave else 0
        facture = Facture.objects.create(
            reservation=reservation,
            client=reservation.user,
            numero=f"FACT-{timezone.now().year}-{timezone.now().strftime('%m%d%H%M')}",
            montant_total=montant,
            date_echeance=timezone.now().date() + timedelta(days=30),
            statut="en_attente"
        )
        
        try:
            notifier_reservation_validee_avec_facture(reservation, facture)
            send_reservation_validated_email(reservation, facture)
        except Exception as e:
            print(f"⚠️ Erreur notification validation réservation : {e}")
        
        try:
            notifier_reservation_validee(reservation)
        except Exception as e:
            print(f"⚠️ Erreur notification réservation validée : {e}")

        return {"message": "Réservation confirmée et facture générée.", "facture_id": facture.id}

    if data.status == "cancelled":
        try:
            notifier_reservation_annulee(reservation)
        except Exception as e:
            print(f"⚠️ Erreur notification : {e}")
        return {"message": "Réservation annulée. Caveau libéré."}

    return {"message": "Statut mis à jour"}


# ==============================================================================
# CONFIRMER INHUMATION (avec règle métier CDC)
# ==============================================================================
@router.put("/{reservation_id}/confirmer-inhumation", response=ConfirmerInhumationOut)
@require_role("admin", "agent")
def confirmer_inhumation(request, reservation_id: int, payload: ConfirmerInhumationIn):
    """
    Confirme l'inhumation avec vérification de date (règle métier CDC).
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)

    if reservation.status != "confirmed":
        raise HttpError(400, "Seule une réservation validée ('confirmed') peut être inhumée.")

    if hasattr(reservation, "inhumation_record"):
        raise HttpError(400, "Cette réservation a déjà été marquée comme inhumée.")

    if not reservation.date_prevue_inhumation:
        raise HttpError(400, "La date prévue d'inhumation n'est pas renseignée sur cette réservation.")

    # Combiner date et heure si fournies
    date_inhumation = payload.date_inhumation
    if payload.heure_inhumation:
        try:
            h, m = map(int, payload.heure_inhumation.split(":"))
            date_inhumation = datetime.combine(date_inhumation, time(h, m))
        except ValueError:
            date_inhumation = datetime.combine(date_inhumation, time(0, 0))
    else:
        date_inhumation = datetime.combine(date_inhumation, time(12, 0))

    # Détection d'inhumation anticipée
    is_anticipée = date_inhumation.date() < reservation.date_prevue_inhumation

    with transaction.atomic():
        # 1. Création de l'acte d'inhumation
        inhumation = Inhumation.objects.create(
            grave=reservation.grave,
            defunt_nom=reservation.deceased_last_name or 'Inconnu',
            defunt_prenom=reservation.deceased_first_name or 'Inconnu',
            defunt_date_deces=reservation.deceased_death_date,
            date_inhumation=date_inhumation,
            observations=payload.observations or "",
            agent_inhumation=request.auth,
            reservation=reservation,
        )

        # 2. Mise à jour de la réservation
        reservation.status = "inhumee"
        reservation.save()

        # 3. Mise à jour du statut du caveau
        grave = reservation.grave
        grave.status = "occupied"
        grave.last_status_change = timezone.now()
        grave.save(update_fields=["status", "last_status_change"])

        # 4. Audit Trail
        try:
            from core.audit import log_action
            log_action(
                user=request.auth,
                action="status_change",
                model_name="Reservation/Inhumation",
                object_id=reservation.id,
                details=f"Inhumation confirmée. Caveau {grave.code} passé à 'occupied'."
            )
        except ImportError:
            pass
        
        try:
            notifier_inhumation_confirmee(inhumation)
        except Exception as e:
            print(f"⚠️ Erreur notification inhumation : {e}")

    message = "Inhumation confirmée avec succès."
    if is_anticipée:
        message += " ⚠️ Inhumation réalisée de manière anticipée."

    return {
        "reservation_id": reservation.id,
        "inhumation_id": inhumation.id,
        "grave_status": grave.status,
        "reservation_status": reservation.status,
        "message": message,
        "is_anticipée": is_anticipée,
    }