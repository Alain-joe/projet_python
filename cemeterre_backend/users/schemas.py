"""
users/schemas.py — Schémas Pydantic avec validation stricte conforme CDC.
Compatible Django Ninja + Pydantic v2
"""
from ninja import Schema
from typing import Optional
from datetime import date
import re
from pydantic import field_validator


# ==============================================================================
# UTILITAIRES DE VALIDATION
# ==============================================================================

def validate_phone_congo(value: str) -> str:
    """Valide un numéro congolais : exactement 9 chiffres, commence par 04, 05 ou 06."""
    cleaned = value.strip()
    if not re.match(r'^(04|05|06)\d{7}$', cleaned):
        raise ValueError("Le numéro doit contenir exactement 9 chiffres et commencer par 04, 05 ou 06.")
    return cleaned


def validate_name(value: str) -> str:
    """Valide un nom/prénom : 2-50 caractères, lettres (avec accents), espaces, tirets, apostrophes."""
    cleaned = value.strip()
    if not re.match(r"^[a-zA-ZÀ-ÿ\s\-']{2,50}$", cleaned):
        raise ValueError("Le nom doit contenir entre 2 et 50 caractères : lettres, espaces, tirets ou apostrophes uniquement.")
    return cleaned.title()


def validate_username(value: str) -> str:
    """Valide un username : 4-30 caractères alphanumériques ou underscores, sans espace."""
    cleaned = value.strip().lower()
    if not re.match(r"^[a-zA-Z0-9_]{4,30}$", cleaned):
        raise ValueError("Le nom d'utilisateur doit contenir 4 à 30 caractères alphanumériques ou underscores, sans espace.")
    return cleaned


def validate_password_strength(value: str) -> str:
    """Valide la force du mot de passe : min 8, 1 maj, 1 min, 1 chiffre, 1 spécial."""
    if len(value) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Le mot de passe doit contenir au moins une majuscule.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Le mot de passe doit contenir au moins une minuscule.")
    if not re.search(r"\d", value):
        raise ValueError("Le mot de passe doit contenir au moins un chiffre.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", value):
        raise ValueError("Le mot de passe doit contenir au moins un caractère spécial (!@#$%^&*...).")
    return value


def validate_email_format(value: str) -> str:
    """Valide le format email et le met en minuscules."""
    cleaned = value.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, cleaned):
        raise ValueError("Format d'email invalide.")
    return cleaned


def validate_sex(value: str) -> str:
    """Valide le sexe : M, F, O ou N."""
    if value not in ['M', 'F', 'O', 'N']:
        raise ValueError("Le sexe doit être M (Masculin), F (Féminin), O (Autre) ou N (Non renseigné).")
    return value


def validate_birth_date(value: Optional[date]) -> Optional[date]:
    """Valide la date de naissance : pas dans le futur, âge ≥ 16 ans."""
    if value is None:
        return None
    from django.utils import timezone
    today = timezone.now().date()
    if value > today:
        raise ValueError("La date de naissance ne peut pas être dans le futur.")
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
    if age < 16:
        raise ValueError(f"L'utilisateur doit avoir au moins 16 ans (âge actuel : {age} ans).")
    if age > 120:
        raise ValueError("Date de naissance incohérente (âge > 120 ans).")
    return value


# ==============================================================================
# SCHÉMAS D'AUTHENTIFICATION
# ==============================================================================

class LoginStep1Schema(Schema):
    username: str
    password: str


class LoginStep2Schema(Schema):
    user_id: int
    code: str

class RefreshTokenSchema(Schema):
    refresh: str


# ==============================================================================
# SCHÉMAS D'INSCRIPTION (Client)
# ==============================================================================

class RegisterSchema(Schema):
    username: str
    email: str
    password: str
    phone: str = ""
    first_name: str
    last_name: str

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_password_strength(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_format(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str) -> str:
        if value:
            return validate_phone_congo(value)
        return value


# ==============================================================================
# SCHÉMAS DE CRÉATION INTERNE (Admin/Secrétariat)
# ==============================================================================

class CreateInternalUserSchema(Schema):
    username: Optional[str] = None
    first_name: str
    last_name: str
    email: str
    sex: str = "N"
    birth_date: Optional[date] = None
    phone: Optional[str] = ""
    role: str
    password: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            value = value.strip()
            if not value:
                return None
            return validate_username(value)
        return value

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str) -> str:
        return validate_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return validate_email_format(value)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return validate_phone_congo(value)
        return value

    @field_validator("sex")
    @classmethod
    def validate_sex_field(cls, value: str) -> str:
        return validate_sex(value)

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date_field(cls, value: Optional[date]) -> Optional[date]:
        return validate_birth_date(value)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in ['admin', 'secretariat', 'agent', 'client']:
            raise ValueError("Le rôle doit être admin, secretariat, agent ou client.")
        return value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return validate_password_strength(value)
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: Optional[str]) -> Optional[str]:
        if value:
            value = value.strip()
            if len(value) < 5 or len(value) > 200:
                raise ValueError("L'adresse doit contenir entre 5 et 200 caractères.")
            return value.title()
        return value

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.strip().title()
        return value


# ==============================================================================
# SCHÉMAS DE SORTIE
# ==============================================================================

class UserOut(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None
    sex: str
    birth_date: Optional[str] = None
    role: str
    is_active: bool
    is_approved: bool
    created_at: Optional[str] = None
    date_joined: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None


# ==============================================================================
# SCHÉMAS DE MISE À JOUR
# ==============================================================================

class UserUpdateSchema(Schema):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    sex: Optional[str] = None
    birth_date: Optional[date] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    address: Optional[str] = None
    city: Optional[str] = None

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: Optional[str]) -> Optional[str]:
        return validate_name(value) if value else value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: Optional[str]) -> Optional[str]:
        return validate_email_format(value) if value else value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: Optional[str]) -> Optional[str]:
        return validate_phone_congo(value) if value else value

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: Optional[str]) -> Optional[str]:
        if value and value not in ['admin', 'secretariat', 'agent', 'client']:
            raise ValueError("Rôle invalide.")
        return value

    @field_validator("address")
    @classmethod
    def validate_address(cls, value: Optional[str]) -> Optional[str]:
        if value:
            value = value.strip()
            if len(value) < 5 or len(value) > 200:
                raise ValueError("L'adresse doit contenir entre 5 et 200 caractères.")
            return value.title()
        return value

    @field_validator("city")
    @classmethod
    def validate_city(cls, value: Optional[str]) -> Optional[str]:
        if value:
            return value.strip().title()
        return value


# ==============================================================================
# SCHÉMAS UTILITAIRES
# ==============================================================================

class GenerateUsernameSchema(Schema):
    first_name: str
    last_name: str

    @field_validator("first_name", "last_name")
    @classmethod
    def clean_names(cls, value: str) -> str:
        return validate_name(value)