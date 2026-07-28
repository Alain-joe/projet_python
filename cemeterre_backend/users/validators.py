"""
users/validators.py — Règles de validation strictes conformes au CDC.
"""
import re
from django.core.exceptions import ValidationError


def validate_phone_number(value: str) -> str:
    """Valide un numéro de téléphone congolais (exactement 9 chiffres, commence par 04, 05 ou 06)."""
    value = value.strip()
    if not re.match(r'^(04|05|06)\d{7}$', value):
        raise ValidationError("Le numéro doit contenir exactement 9 chiffres et commencer par 04, 05 ou 06.")
    return value


def validate_name(value: str) -> str:
    """Valide un nom ou prénom : 2 à 50 caractères, lettres (avec accents), espaces, tirets, apostrophes."""
    value = value.strip()
    if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']{2,50}$", value):
        raise ValidationError("Le nom doit contenir entre 2 et 50 caractères, uniquement des lettres, espaces, tirets ou apostrophes.")
    return value.title() # Capitalize la première lettre de chaque mot


def validate_username(value: str) -> str:
    """Valide un nom d'utilisateur : 4 à 30 caractères alphanumériques ou underscores, sans espace."""
    value = value.strip()
    if not re.match(r"^[a-zA-Z0-9_]{4,30}$", value):
        raise ValidationError("Le nom d'utilisateur doit contenir 4 à 30 caractères alphanumériques ou underscores, sans espace.")
    return value.lower()


def validate_password(value: str) -> str:
    """Valide la force du mot de passe (min 8, 1 maj, 1 min, 1 chiffre, 1 spécial)."""
    if len(value) < 8:
        raise ValidationError("Le mot de passe doit contenir au moins 8 caractères.")
    if not re.search(r"[A-Z]", value):
        raise ValidationError("Le mot de passe doit contenir au moins une majuscule.")
    if not re.search(r"[a-z]", value):
        raise ValidationError("Le mot de passe doit contenir au moins une minuscule.")
    if not re.search(r"\d", value):
        raise ValidationError("Le mot de passe doit contenir au moins un chiffre.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValidationError("Le mot de passe doit contenir au moins un caractère spécial.")
    return value