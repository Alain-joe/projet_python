"""
finance/email_utils.py — Envoi de la facture par email sécurisé (TLS).

Cahier des charges 2.4 : "envoi par email sécurisé."
"""

from __future__ import annotations

import logging

import logging
from django.utils import timezone  # <-- AJOUTE CETTE LIGNE
from django.core.mail import EmailMessage
# ... le reste de ton code ...
from django.core.mail import EmailMessage
from django.conf import settings

from .pdf_utils import generate_facture_pdf

logger = logging.getLogger(__name__)


def send_facture_by_email(facture) -> bool:
    """
    Génère le PDF de la facture et l'envoie par email au client.
    Retourne True si l'envoi a réussi, False sinon (ne lève jamais
    d'exception : un échec d'email ne doit jamais faire échouer la
    validation de la réservation elle-même).
    """
    try:
        pdf_bytes = generate_facture_pdf(facture)

        email = EmailMessage(
            subject=f"Votre facture {facture.numero} — Cimetière Connect",
            body=(
                f"Bonjour,\n\n"
                f"Votre réservation a été validée. Vous trouverez ci-joint la facture "
                f"n°{facture.numero} d'un montant de {facture.montant_total} FCFA, "
                f"à régler avant le {facture.date_echeance.strftime('%d/%m/%Y') if facture.date_echeance else '-'}.\n\n"
                f"Cordialement,\nL'administration du cimetière."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[facture.client.email],
        )
        email.attach(f"facture_{facture.numero}.pdf", pdf_bytes, "application/pdf")
        email.send(fail_silently=False)
        return True

    except Exception as exc:
        # On journalise l'échec mais on ne bloque jamais le workflow de
        # validation de réservation pour un problème d'envoi d'email.
        logger.error(f"Échec de l'envoi de la facture {facture.numero} par email : {exc}")
        return False