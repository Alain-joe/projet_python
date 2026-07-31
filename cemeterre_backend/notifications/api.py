"""
projet_cimetiere/cemeterre_backend/notifications/api.py
CORRECTION : request.user -> request.auth (ce projet utilise JWTAuth
de ninja_jwt, qui place l'utilisateur authentifié dans request.auth,
pas request.user qui reste AnonymousUser ici. Ce bug faisait que
Notification.objects.filter(destinataire=request.user) ne trouvait
jamais aucune notification, quel que soit l'utilisateur connecté.

CORRECTION ADDITIONNELLE : marquer_lu utilisait .get() sans gestion
de DoesNotExist, ce qui renvoyait une erreur 500 brute si la
notification n'existait pas ou n'appartenait pas à l'utilisateur.
Utilisation de get_object_or_404 pour renvoyer un 404 propre.
"""
from ninja import Router
from ninja.errors import HttpError
from ninja_jwt.authentication import JWTAuth
from django.shortcuts import get_object_or_404

from .models import Notification
from .schemas import NotificationSchema

router = Router(auth=JWTAuth())


# =========================
# LIST NOTIFICATIONS
# =========================
@router.get("/notifications", response=list[NotificationSchema])
def mes_notifications(request):
    return Notification.objects.filter(
        destinataire=request.auth
    ).order_by("-created_at")


# =========================
# UNREAD COUNT
# =========================
@router.get("/notifications/unread-count")
def notifications_non_lues(request):
    count = Notification.objects.filter(
        destinataire=request.auth,
        lu=False
    ).count()

    return {"non_lues": count}


# =========================
# MARK AS READ
# =========================
@router.put("/notifications/{notification_id}/read")
def marquer_lu(request, notification_id: int):
    notif = get_object_or_404(
        Notification,
        id=notification_id,
        destinataire=request.auth
    )

    notif.lu = True
    notif.save(update_fields=["lu"])

    return {"message": "notification lue"}


# =========================
# MARK ALL READ
# =========================
@router.put("/notifications/read-all")
def marquer_toutes_lues(request):
    Notification.objects.filter(
        destinataire=request.auth,
        lu=False
    ).update(lu=True)

    return {"message": "toutes lues"}