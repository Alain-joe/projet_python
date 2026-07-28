"""
notifications/utils_extended.py — Fonctions de notification étendues.
CORRECTION : Utilisation des vrais champs du modèle Notification
(destinataire, type_notification, titre, message).
"""
from django.utils import timezone
from .models import Notification
from .utils import notifier_admins, notifier_user
from users.models import User


def notifier_paiement_recu(facture):
    """Notifie les admins/secrétariat qu'un paiement a été reçu."""
    if not facture or not facture.reservation:
        return
    
    reservation = facture.reservation
    client = facture.client
    
    dernier_paiement = facture.paiements.last()
    mode = dernier_paiement.mode_paiement if dernier_paiement else "Non précisé"
    
    titre = f"Nouveau paiement reçu - {client.username}"
    message = (
        f"Client : {client.first_name or ''} {client.last_name or client.username}\n"
        f"Réservation : {reservation.grave.code}\n"
        f"Facture : {facture.numero}\n"
        f"Montant : {facture.montant_total:,.0f} FCFA\n"
        f"Mode : {mode}\n\n"
        f"Cette réservation est maintenant prête pour la création d'une concession."
    )
    
    notifier_admins(
        type_notification='facture_payee',
        titre=titre,
        message=message
    )


def notifier_concession_creee(concession):
    """Notifie le client que sa concession a été créée."""
    if not concession or not concession.user:
        return
    
    titre = "Votre concession a été créée"
    message = (
        f"Félicitations {concession.user.first_name or concession.user.username} !\n\n"
        f"Votre concession pour le caveau {concession.grave.code} a été officiellement créée.\n\n"
        f"Type : {concession.get_type_concession_display()}\n"
        f"Début : {concession.date_debut.strftime('%d/%m/%Y')}\n"
        f"Fin : {concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else 'Perpétuelle'}\n\n"
        f"Vous pouvez télécharger votre contrat depuis votre espace personnel."
    )
    
    notifier_user(
        user=concession.user,
        type_notification='concession_creee',
        titre=titre,
        message=message
    )


def notifier_concession_expiration(concession, days_before):
    """Notifie le client et les admins qu'une concession arrive à expiration."""
    if not concession or not concession.user:
        return
    
    titre = f"Votre concession arrive à expiration dans {days_before} jours"
    message = (
        f"Bonjour {concession.user.first_name or concession.user.username},\n\n"
        f"Votre concession pour le caveau {concession.grave.code} arrive à expiration le {concession.date_fin.strftime('%d/%m/%Y')}.\n\n"
        f"Nous vous invitons à procéder au renouvellement dès que possible."
    )
    
    notifier_user(
        user=concession.user,
        type_notification='concession_expirante',
        titre=titre,
        message=message
    )
    
    titre_admin = f"Concession à renouveler - J-{days_before}"
    message_admin = (
        f"Client : {concession.user.username}\n"
        f"Caveau : {concession.grave.code}\n"
        f"Expiration : {concession.date_fin.strftime('%d/%m/%Y')}"
    )
    
    notifier_admins(
        type_notification='concession_expirante',
        titre=titre_admin,
        message=message_admin
    )


def notifier_concession_expiree(concession):
    """Notifie les admins qu'une concession a expiré."""
    if not concession:
        return
    
    titre = "Concession expirée"
    message = (
        f"Client : {concession.user.username}\n"
        f"Caveau : {concession.grave.code}\n"
        f"Date d'expiration : {concession.date_fin.strftime('%d/%m/%Y')}\n\n"
        f"Action requise : Engager la procédure administrative."
    )
    
    notifier_admins(
        type_notification='concession_expiree',
        titre=titre,
        message=message
    )


def notifier_inhumation_confirmee(inhumation):
    """Notifie le client que l'inhumation a été confirmée."""
    if not inhumation or not inhumation.reservation:
        return
    
    client = inhumation.reservation.user
    titre = "Inhumation confirmée"
    message = (
        f"Bonjour {client.first_name or client.username},\n\n"
        f"L'inhumation de {inhumation.defunt_prenom} {inhumation.defunt_nom} au caveau {inhumation.grave.code} a été confirmée.\n"
        f"Date : {inhumation.date_inhumation.strftime('%d/%m/%Y')}"
    )
    
    notifier_user(
        user=client,
        type_notification='inhumation_confirmee',
        titre=titre,
        message=message
    )


def notifier_reservation_validee_avec_facture(reservation, facture):
    """Notifie le client que sa réservation est validée avec facture en attente."""
    if not reservation or not reservation.user or not facture:
        return
    
    titre = "Réservation validée - Paiement requis"
    message = (
        f"Bonjour {reservation.user.first_name or reservation.user.username},\n\n"
        f"Votre réservation pour le caveau {reservation.grave.code} a été validée.\n\n"
        f"Facture N° : {facture.numero}\n"
        f"Montant à payer : {facture.montant_total:,.0f} FCFA\n"
        f"Date limite : {facture.date_echeance.strftime('%d/%m/%Y')}\n\n"
        f"Veuillez procéder au paiement pour finaliser votre dossier."
    )
    
    notifier_user(
        user=reservation.user,
        type_notification='reservation_validee',
        titre=titre,
        message=message
    )

def notifier_nouveau_signalement_caveau(signalement):
    """Notifie les administrateurs qu'un nouveau signalement de caveau a été créé."""
    if not signalement or not signalement.grave:
        return
    
    titre = f"🔴 Nouveau signalement de caveau - {signalement.grave.code}"
    message = (
        f"Un agent a signalé un problème sur le caveau {signalement.grave.code}.\n\n"
        f"Motif : {signalement.motif}\n\n"
        f"Veuillez consulter le dossier et valider ou rejeter ce signalement."
    )
    
    notifier_admins(
        type_notification='signalement_caveau',
        titre=titre,
        message=message
    )