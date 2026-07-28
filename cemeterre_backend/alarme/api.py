# projet_cimetiere/cemeterre_backend/alarme/api.py

from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import timedelta

from .models import Alarm
from .schemas import AlarmSchema, AlarmCreateSchema, AlarmUpdateSchema
from users.models import User
from cemetery.models import Concession
from finance.models import Facture
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Alarmes"])


@router.get("/alarms", response=list[AlarmSchema])
def list_my_alarms(request, status: str = None):
    """Liste mes alarmes (avec filtre optionnel par statut)"""
    qs = Alarm.objects.filter(user=request.user)
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-created_at")


@router.get("/alarms/all", response=list[AlarmSchema])
@require_role("admin")
def list_all_alarms(request, type_alarm: str = None):
    """Liste TOUTES les alarmes du système (Réservé aux Admins)"""
    qs = Alarm.objects.all().select_related("user")
    if type_alarm:
        qs = qs.filter(type_alarm=type_alarm)
    return qs.order_by("-created_at")


@router.post("/alarms")
def create_alarm(request, data: AlarmCreateSchema):
    """Créer une alarme."""
    if request.auth.role == "admin" and data.user_id:
        target_user = get_object_or_404(User, id=data.user_id)
    else:
        target_user = request.auth

    alarm = Alarm.objects.create(
        type_alarm=data.type_alarm,
        message=data.message,
        user=target_user,
        reservation_id=data.reservation_id,
        facture_id=data.facture_id,
        concession_id=data.concession_id,
        exhumation_id=data.exhumation_id,
    )

    return {"message": "Alarme créée avec succès", "id": alarm.id}


@router.put("/alarms/{alarm_id}")
def update_alarm(request, alarm_id: int, data: AlarmUpdateSchema):
    """Marquer une alarme comme lue ou résolue"""
    alarm = get_object_or_404(Alarm, id=alarm_id, user=request.user)

    if data.status is not None:
        alarm.status = data.status
    if data.is_read is not None:
        alarm.is_read = data.is_read
        
    alarm.save()
    return {"message": "Alarme mise à jour", "status": alarm.status, "is_read": alarm.is_read}


@router.delete("/alarms/{alarm_id}")
def ignore_alarm(request, alarm_id: int):
    """Ignorer une alarme (suppression logique)"""
    alarm = get_object_or_404(Alarm, id=alarm_id, user=request.user)
    alarm.status = "ignored"
    alarm.save()
    return {"message": "Alarme ignorée"}


# ==============================================================================
# NOUVEAU : GÉNÉRATION AUTOMATIQUE DES ALARMES
# ==============================================================================

def generate_automatic_alarms():
    """Vérifie et crée automatiquement les alarmes pour concessions expirantes et retards de paiement"""
    today = timezone.now().date()
    alarms_created = 0

    # 1. Concessions expirant dans les 30 prochains jours
    threshold = today + timedelta(days=30)
    expiring_concessions = Concession.objects.filter(
        status='active',
        type_concession='temporaire',
        date_fin__lte=threshold,
        date_fin__gte=today
    ).select_related('user', 'grave')

    for conc in expiring_concessions:
        if not Alarm.objects.filter(concession=conc, type_alarm='concession_expiration', status='active').exists():
            Alarm.objects.create(
                type_alarm='concession_expiration',
                message=f"La concession du caveau {conc.grave.code} expire le {conc.date_fin}. Pensez à la renouveler.",
                user=conc.user,
                concession=conc,
                status='active'
            )
            alarms_created += 1

    # 2. Retards de paiement (Factures en attente dont la date d'échéance est passée)
    late_factures = Facture.objects.filter(
        statut='en_attente',
        date_echeance__lt=today
    ).select_related('client')

    for fact in late_factures:
        if not Alarm.objects.filter(facture=fact, type_alarm='payment_delay', status='active').exists():
            Alarm.objects.create(
                type_alarm='payment_delay',
                message=f"La facture {fact.numero} de {fact.montant_total} FCFA est en retard de paiement (échéance: {fact.date_echeance}).",
                user=fact.client,
                facture=fact,
                status='active'
            )
            alarms_created += 1
            
    return alarms_created


@router.post("/alarms/auto-check")
@require_role("admin")
def trigger_auto_alarms(request):
    """
    Déclenche manuellement la vérification des alarmes.
    (Idéalement, cette fonction serait appelée par un Cron Job ou Celery en production).
    """
    count = generate_automatic_alarms()
    return {"message": f"Vérification terminée. {count} nouvelle(s) alarme(s) générée(s)."}