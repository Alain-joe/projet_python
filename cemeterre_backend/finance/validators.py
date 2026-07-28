"""
finance/validators.py — Validateurs pour les moyens de paiement.
CORRECTION : Validation plus permissive pour accepter différents formats de numéros.
"""
import re
from django.core.exceptions import ValidationError


def validate_mtn_number(phone: str):
    """Valide un numéro MTN (doit commencer par 06 et avoir au moins 9 chiffres)"""
    phone = phone.strip()
    if not re.match(r'^06\d{7,}$', phone):
        raise ValidationError("Le numéro MTN doit commencer par 06 et contenir au moins 9 chiffres.")
    return phone


def validate_airtel_number(phone: str):
    """Valide un numéro Airtel (doit commencer par 04 ou 05 et avoir au moins 9 chiffres)"""
    phone = phone.strip()
    if not re.match(r'^(04|05)\d{7,}$', phone):
        raise ValidationError("Le numéro Airtel doit commencer par 04 ou 05 et contenir au moins 9 chiffres.")
    return phone


def validate_montant_paiement(montant: float, solde_restant: float):
    """Valide que le montant est positif et ne dépasse pas le solde"""
    if montant <= 0:
        raise ValidationError("Le montant doit être strictement positif.")
    if montant > solde_restant:
        raise ValidationError(f"Le montant saisi dépasse le solde restant de {solde_restant:,.0f} FCFA.")
    return montant