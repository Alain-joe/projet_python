from .models import Notification
from users.models import User


def notifier_admins(type_notification, titre, message, exclude_user=None):
    """
    Envoie une notification à tous les admins et secrétariats.
    exclude_user permet d'éviter qu'une personne se notifie elle-même
    (ex: un membre du secrétariat qui vient de créer un compte).
    """
    admins = User.objects.filter(role__in=['admin', 'secretariat'])
    if exclude_user is not None:
        admins = admins.exclude(id=exclude_user.id)
    for admin in admins:
        Notification.objects.create(
            destinataire=admin,
            type_notification=type_notification,
            titre=titre,
            message=message,
        )


def notifier_user(user, type_notification, titre, message):
    """Envoie une notification à un utilisateur spécifique"""
    Notification.objects.create(
        destinataire=user,
        type_notification=type_notification,
        titre=titre,
        message=message,
    )


def notifier_nouvelle_reservation(reservation):
    notifier_admins(
        type_notification='nouvelle_reservation',
        titre='Nouvelle réservation',
        message=f"Nouvelle réservation de {reservation.user.username} pour le caveau {reservation.grave.code}."
    )


def notifier_reservation_validee(reservation):
    notifier_user(
        user=reservation.user,
        type_notification='reservation_validee',
        titre='Réservation confirmée',
        message=f"Votre réservation pour le caveau {reservation.grave.code} a été confirmée."
    )


def notifier_reservation_annulee(reservation):
    notifier_user(
        user=reservation.user,
        type_notification='reservation_annulee',
        titre='Réservation annulée',
        message=f"Votre réservation pour le caveau {reservation.grave.code} a été annulée."
    )


def notifier_nouvel_utilisateur(user, cree_par=None):
    """
    Prévient les admins/secrétariat qu'un nouveau compte a été créé.
    cree_par permet d'exclure la personne qui a elle-même créé le
    compte (elle n'a pas besoin d'être notifiée de sa propre action).
    """
    role_label = dict(User.ROLE_CHOICES).get(user.role, user.role)
    notifier_admins(
        type_notification='nouvel_utilisateur',
        titre='Nouvel utilisateur créé',
        message=f"Le compte {role_label} de {user.first_name} {user.last_name} ({user.username}) a été créé.",
        exclude_user=cree_par,
    )


def notifier_concessions_expirantes():
    """À appeler périodiquement pour alerter sur les concessions qui expirent"""
    from django.utils import timezone
    from cemetery.models import Concession
    threshold = timezone.now().date() + timezone.timedelta(days=30)
    concessions = Concession.objects.filter(
        status='active',
        date_fin__lte=threshold,
        type_concession='temporaire'
    )
    for concession in concessions:
        notifier_admins(
            type_notification='concession_expirante',
            titre='Concession expirante',
            message=f"La concession du caveau {concession.grave.code} expire le {concession.date_fin}."
        )