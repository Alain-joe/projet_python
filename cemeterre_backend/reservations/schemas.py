"""
projet_cimetiere/cemeterre_backend/reservations/schemas.py
Schemas Django Ninja pour les réservations.
CORRECTION : Ajout de date_prevue_inhumation dans ReservationCreateSchema
"""
from ninja import Schema
from datetime import date, datetime
from typing import Optional


class ReservationCreateSchema(Schema):
    """Schema pour créer une réservation (entrée)"""
    grave_id: int
    user_id: Optional[int] = None
    client_username: Optional[str] = None
    note: Optional[str] = ""
    deceased_first_name: Optional[str] = ""
    deceased_last_name: Optional[str] = ""
    deceased_birth_date: Optional[date] = None
    deceased_death_date: Optional[date] = None
    
    # ✅ CORRECTION : Date prévue d'inhumation (essentielle pour le workflow)
    date_prevue_inhumation: Optional[date] = None


class ReservationStatusSchema(Schema):
    """Schema pour changer le statut d'une réservation"""
    status: str
    note_validation: Optional[str] = ""


class ReservationSchema(Schema):
    """Schema de sortie pour les réservations"""
    id: int
    user_id: int
    grave_id: int
    status: str
    reservation_date: datetime
    note: Optional[str] = ""
    deceased_first_name: Optional[str] = ""
    deceased_last_name: Optional[str] = ""
    deceased_birth_date: Optional[date] = None
    deceased_death_date: Optional[date] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    
    # ✅ CORRECTION : Date prévue d'inhumation
    date_prevue_inhumation: Optional[date] = None

    # Champs enrichis
    grave_code: Optional[str] = None
    client_username: Optional[str] = None
    section_name: Optional[str] = None
    grave_price: Optional[float] = None

    @staticmethod
    def resolve_grave_code(obj) -> Optional[str]:
        if hasattr(obj, 'grave') and obj.grave:
            return obj.grave.code
        return None

    @staticmethod
    def resolve_client_username(obj) -> Optional[str]:
        if hasattr(obj, 'user') and obj.user:
            return obj.user.username
        return None

    @staticmethod
    def resolve_section_name(obj) -> Optional[str]:
        if hasattr(obj, 'grave') and obj.grave and hasattr(obj.grave, 'section') and obj.grave.section:
            return obj.grave.section.name
        return None

    @staticmethod
    def resolve_grave_price(obj) -> Optional[float]:
        if hasattr(obj, 'grave') and obj.grave:
            return float(obj.grave.price) if obj.grave.price else 0.0
        return 0.0