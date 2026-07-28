"""
cemetery/emails_extended.py — Templates emails étendus.
Compatible avec le système d'emails existant.
"""
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone


def send_payment_confirmation_email(facture):
    """Envoie un email de confirmation après un paiement."""
    if not facture or not facture.client or not facture.client.email:
        return False
    
    try:
        # ✅ CORRECTION : Récupérer le dernier paiement pour connaître le mode
        dernier_paiement = facture.paiements.last()
        mode = dernier_paiement.mode_paiement if dernier_paiement else "Non précisé"
        
        subject = f"Confirmation de paiement - Facture {facture.numero}"
        message = f"""
Bonjour {facture.client.first_name or facture.client.username},

Nous vous confirmons la réception de votre paiement.

Détails :
- Facture N° : {facture.numero}
- Montant réglé : {facture.montant_total:,.0f} FCFA
- Mode de paiement : {mode}
- Date : {facture.paid_at.strftime('%d/%m/%Y') if facture.paid_at else 'Aujourd\'hui'}

Votre dossier est maintenant à jour.
Cordialement,
Le Cimetière Municipal de Pointe-Noire
        """.strip()
        
        from django.core.mail import send_mail
        from django.conf import settings
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [facture.client.email], fail_silently=False)
        return True
    except Exception as e:
        print(f"⚠️ Erreur envoi email confirmation paiement: {e}")
        return False


def send_concession_created_email(concession):
    """
    Envoie un email au client après la création de sa concession.
    """
    if not concession or not concession.user or not concession.user.email:
        return False
    
    try:
        subject = f"Votre concession a été créée - N° CONC-{concession.id:06d}"
        message = f"""
Bonjour {concession.user.first_name or concession.user.username},

Nous avons le plaisir de vous informer que votre concession funéraire a été officiellement créée.

Détails de votre concession :
- Caveau : {concession.grave.code}
- Section : {concession.grave.section.name if concession.grave.section else 'N/A'}
- Type : {concession.get_type_concession_display()}
- Date de début : {concession.date_debut.strftime('%d/%m/%Y')}
- Date de fin : {concession.date_fin.strftime('%d/%m/%Y') if concession.date_fin else 'Perpétuelle'}
- Montant : {concession.montant:,.0f} FCFA

Vous pouvez télécharger votre contrat depuis votre espace personnel.

En cas de question, n'hésitez pas à contacter le secrétariat.

Cordialement,
Le Cimetière Municipal de Pointe-Noire
        """.strip()
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [concession.user.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"⚠️ Erreur envoi email concession créée: {e}")
        return False


def send_expiration_warning_email(concession, days_before):
    """
    Envoie un email d'avertissement au client avant l'expiration de sa concession.
    """
    if not concession or not concession.user or not concession.user.email:
        return False
    
    try:
        urgency = "URGENT" if days_before <= 30 else "Rappel"
        subject = f"{urgency} - Votre concession arrive à expiration dans {days_before} jours"
        message = f"""
Bonjour {concession.user.first_name or concession.user.username},

Votre concession pour le caveau {concession.grave.code} arrive à expiration dans {days_before} jours,
soit le {concession.date_fin.strftime('%d/%m/%Y')}.

Pour éviter toute interruption, nous vous invitons à procéder au renouvellement dès que possible.

Détails de votre concession actuelle :
- Caveau : {concession.grave.code}
- Type : {concession.get_type_concession_display()}
- Date d'expiration : {concession.date_fin.strftime('%d/%m/%Y')}

Options de renouvellement disponibles :
- Temporaire (durée personnalisée)
- Trentenaire (30 ans)
- Cinquantenaire (50 ans)

Contactez le secrétariat au +242 06 910 37 15 ou par email à contact@cimetiere-pn.cg
pour engager la procédure de renouvellement.

Cordialement,
Le Cimetière Municipal de Pointe-Noire
        """.strip()
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [concession.user.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"⚠️ Erreur envoi email expiration: {e}")
        return False


def send_reservation_validated_email(reservation, facture):
    """
    Envoie un email au client après la validation de sa réservation.
    """
    if not reservation or not reservation.user or not reservation.user.email:
        return False
    
    try:
        subject = f"Votre réservation a été validée - Caveau {reservation.grave.code}"
        message = f"""
Bonjour {reservation.user.first_name or reservation.user.username},

Votre réservation pour le caveau {reservation.grave.code} a été validée avec succès.

Détails de votre réservation :
- Caveau : {reservation.grave.code}
- Section : {reservation.grave.section.name if reservation.grave.section else 'N/A'}
- Date de réservation : {reservation.reservation_date.strftime('%d/%m/%Y')}

Facture à régler :
- Numéro : {facture.numero}
- Montant : {facture.montant_total:,.0f} FCFA
- Date limite : {facture.date_echeance.strftime('%d/%m/%Y')}

Veuillez procéder au paiement pour finaliser votre dossier.
Une fois le paiement confirmé, le secrétariat vous contactera pour la création de votre concession.

Cordialement,
Le Cimetière Municipal de Pointe-Noire
        """.strip()
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [reservation.user.email],
            fail_silently=False
        )
        return True
    except Exception as e:
        print(f"⚠️ Erreur envoi email réservation validée: {e}")
        return False