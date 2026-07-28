# projet_cimetiere/cemeterre_backend/reports/schemas.py

from ninja import Schema
from typing import List, Optional


class SectionStatsSchema(Schema):
    """Statistiques d'occupation pour une section"""
    id: int
    name: str
    total: int
    occupied: int
    available: int
    rate: float


class MonthlyRevenueSchema(Schema):
    """Revenus pour un mois donné"""
    month: str
    amount: float


class DashboardStatsSchema(Schema):
    """
    Statistiques complètes du Dashboard (Conforme CDC Section 2.2) :
    - Statistiques globales des caveaux
    - Taux d'occupation par section
    - Revenus financiers (total + mensuel)
    """
    total_graves: int
    free: int
    reserved: int
    occupied: int
    unavailable: int
    occupation_rate: float
    saturation_rate: float
    
    # ✅ Nouveaux champs conformes CDC
    sections: Optional[List[SectionStatsSchema]] = []
    total_revenue: Optional[float] = 0.0
    monthly_revenue: Optional[List[MonthlyRevenueSchema]] = []


class ExportMessageSchema(Schema):
    message: str