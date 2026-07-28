# projet_cimetiere/cemeterre_backend/finance/schemas.py

from ninja import Schema
from datetime import date, datetime
from decimal import Decimal
from typing import Optional


class FactureCreateSchema(Schema):
    reservation_id: int
    montant_total: Decimal
    date_echeance: Optional[date] = None


class FactureSchema(Schema):
    id: int
    numero: str
    montant_total: Decimal
    montant_paye: Decimal
    montant_restant: Decimal
    statut: str
    is_paid: bool
    date_echeance: Optional[date]
    reservation_id: int
    client_id: int
    created_at: datetime
    
    # ✅ Champs enrichis pour le frontend
    client_username: Optional[str] = None
    client_email: Optional[str] = None

    # ✅ Resolvers qui peuplent automatiquement les champs ci-dessus
    @staticmethod
    def resolve_client_username(obj) -> Optional[str]:
        return obj.client.username if obj.client else "Inconnu"

    @staticmethod
    def resolve_client_email(obj) -> Optional[str]:
        return obj.client.email if obj.client else ""


# ✅ NOUVEAUX SCHEMAS DE PAIEMENT SPÉCIFIQUES
class PaiementEspecesSchema(Schema):
    montant: Decimal
    reference: Optional[str] = ""


class PaiementMobileSchema(Schema):
    phone: str
    montant: Decimal


class PaiementVirementSchema(Schema):
    montant: Decimal
    reference_virement: str


class PaiementHistoriqueSchema(Schema):
    id: int
    montant: float
    mode_paiement: str
    reference: str
    date_paiement: datetime
    traite_par: Optional[str] = None
    statut_validation: str

    @staticmethod
    def resolve_traite_par(obj) -> Optional[str]:
        return obj.traite_par.username if obj.traite_par else "Système"


class StatsFinanceSchema(Schema):
    total_factures: int
    total_attendu: float
    total_paye: float
    total_restant: float
    payees: int
    en_attente: int
    partielles: int