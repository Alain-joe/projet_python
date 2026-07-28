"""
projet_cimetiere/cemeterre_backend/notifications/api.py
CORRECTION : request.user -> request.auth (ce projet utilise JWTAuth
de ninja_jwt, qui place l'utilisateur authentifié dans request.auth,
pas request.user qui reste AnonymousUser ici. Ce bug faisait que
Notification.objects.filter(destinataire=request.user) ne trouvait
jamais aucune notification, quel que soit l'utilisateur connecté.
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth

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
    )


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

    notif = Notification.objects.get(
        id=notification_id,
        destinataire=request.auth
    )

    notif.lu = True
    notif.save()

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