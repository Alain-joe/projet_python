# projet_cimetiere/cemeterre_backend/alarme/schemas.py

from ninja import Schema
from datetime import datetime
from typing import Optional


class AlarmSchema(Schema):
    id: int
    type_alarm: str
    status: str
    message: str
    user_id: int  # Ajouté pour savoir à qui appartient l'alarme
    is_read: bool
    created_at: datetime
    
    # IDs des objets liés (optionnels)
    reservation_id: Optional[int] = None
    facture_id: Optional[int] = None
    concession_id: Optional[int] = None
    exhumation_id: Optional[int] = None


class AlarmCreateSchema(Schema):
    type_alarm: str
    message: str
    # user_id est optionnel : si non fourni, on utilise request.auth
    user_id: Optional[int] = None 
    
    reservation_id: Optional[int] = None
    facture_id: Optional[int] = None
    concession_id: Optional[int] = None
    exhumation_id: Optional[int] = None


class AlarmUpdateSchema(Schema):
    status: Optional[str] = None
    is_read: Optional[bool] = None