"""
projet_cimetiere/cemeterre_backend/cemetery/emails.py
Envoi des emails liés aux concessions.
Conforme CDC §6 : Notifications et alertes.
"""

import logging
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from .pdf_utils import generate_concession_contrat_pdf

logger = logging.getLogger(__name__)


def send_concession_contrat_email(concession, facture=None, is_renewal=False):
    """
    Envoie le contrat de concession par email au titulaire.
    Conforme CDC §2.4 : Envoi par email sécurisé.
    """
    try:
        if not concession.user.email:
            logger.warning(f"Pas d'email pour l'utilisateur {concession.user.id}")
            return False

        pdf_bytes = generate_concession_contrat_pdf(concession)
        
        if is_renewal:
            subject = f"Renouvellement de votre concession N° CONC-{concession.id:06d}"
            body = (
                f"Bonjour {concession.user.first_name or concession.user.username},\n\n"
                f"Votre concession funéraire N° CONC-{concession.id:06d} (Caveau {concession.grave.code}) "
                f"a été renouvelée avec succès.\n\n"
                f"Nouvelle date d'échéance : {concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else 'Perpétuelle'}\n\n"
                f"Veuillez trouver ci-joint votre nouveau contrat.\n\n"
                f"Cordialement,\nL'administration du Cimetière Municipal de Pointe-Noire"
            )
        else:
            subject = f"Votre contrat de concession N° CONC-{concession.id:06d}"
            body = (
                f"Bonjour {concession.user.first_name or concession.user.username},\n\n"
                f"Nous avons le plaisir de vous confirmer l'attribution de la concession funéraire "
                f"N° CONC-{concession.id:06d} pour le caveau {concession.grave.code}.\n\n"
                f"Détails :\n"
                f"• Type : {'Temporaire' if concession.type_concession == 'temporaire' else 'Perpétuelle'}\n"
                f"• Durée : {concession.duree_annees or 'Perpétuelle'} ans\n"
                f"• Date de début : {concession.date_debut.strftime('%d/%m/%Y')}\n"
                f"• Date de fin : {concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else 'Perpétuelle'}\n\n"
                f"Veuillez trouver ci-joint votre contrat signé.\n\n"
                f"Cordialement,\nL'administration du Cimetière Municipal de Pointe-Noire"
            )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[concession.user.email],
        )
        email.attach(f"Contrat_Concession_{concession.id:06d}.pdf", pdf_bytes, "application/pdf")
        email.send(fail_silently=False)
        
        logger.info(f"✅ Email contrat envoyé pour concession {concession.id}")
        return True

    except Exception as exc:
        logger.error(f"❌ Erreur envoi email concession {concession.id}: {exc}")
        return False


def send_expiration_alert_email(concession, days=15):
    """
    Alerte d'expiration envoyée au client J-15.
    Conforme CDC §6 : Alertes Client.
    """
    try:
        if not concession.user.email:
            return False

        subject = f"⚠️ Rappel : Votre concession expire dans {days} jours"
        body = (
            f"Bonjour {concession.user.first_name or concession.user.username},\n\n"
            f"Nous vous informons que votre concession funéraire N° CONC-{concession.id:06d} "
            f"(Caveau {concession.grave.code}) arrive à échéance le "
            f"{concession.date_fin.strftime('%d/%m/%Y')}.\n\n"
            f"Pour éviter la perte de vos droits, nous vous invitons à :\n"
            f"1. Contacter notre secrétariat au +242 06 910 37 15\n"
            f"2. Ou vous connecter à votre espace client pour renouveler en ligne\n\n"
            f"À défaut de renouvellement, la concession sera considérée comme expirée "
            f"conformément à la réglementation en vigueur.\n\n"
            f"Cordialement,\nL'administration du Cimetière Municipal de Pointe-Noire"
        )

        email = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[concession.user.email],
        )
        email.send(fail_silently=False)
        
        logger.info(f"✅ Alerte expiration J-{days} envoyée pour concession {concession.id}")
        return True

    except Exception as exc:
        logger.error(f"❌ Erreur alerte expiration {concession.id}: {exc}")
        return False