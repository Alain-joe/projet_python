"""
finance/schemas_reports.py — Schémas Pydantic pour les rapports financiers.
Compatible Django Ninja.
"""
from ninja import Schema
from typing import Optional, List
from datetime import date, datetime
from pydantic import condecimal


# ==============================================================================
# KPIs DU DASHBOARD FINANCIER
# ==============================================================================
class FinanceDashboardSchema(Schema):
    """Statistiques financières pour le dashboard."""
    # Chiffre d'affaires
    ca_jour: float = 0.0
    ca_mois: float = 0.0
    ca_annee: float = 0.0
    
    # Nombre de paiements
    paiements_jour: int = 0
    paiements_mois: int = 0
    paiements_annee: int = 0
    
    # Factures
    factures_en_attente: int = 0
    factures_payees: int = 0
    factures_annulees: int = 0
    montant_en_attente: float = 0.0
    
    # Concessions
    concessions_creees_mois: int = 0
    concessions_creees_annee: int = 0
    
    # Recettes par type
    recettes_temporaire: float = 0.0
    recettes_trentenaire: float = 0.0
    recettes_cinquantenaire: float = 0.0
    recettes_perpetuelle: float = 0.0
    
    # Évolution mensuelle (12 derniers mois)
    evolution_mensuelle: List[dict] = []


# ==============================================================================
# RAPPORT FINANCIER
# ==============================================================================
class RapportFinancierSchema(Schema):
    """Rapport financier pour une période donnée."""
    periode_debut: date
    periode_fin: date
    type_rapport: str  # "journalier", "mensuel", "annuel", "personnalise"
    
    # Totaux
    total_paiements: int = 0
    total_montant: float = 0.0
    total_factures: int = 0
    total_concessions: int = 0
    
    # Détail par mode de paiement
    par_mode_paiement: List[dict] = []
    
    # Détail par type de concession
    par_type_concession: List[dict] = []
    
    # Évolution journalière
    evolution_journaliere: List[dict] = []


# ==============================================================================
# PAIEMENT
# ==============================================================================
class PaiementOut(Schema):
    """Schéma de sortie pour un paiement."""
    id: int
    numero: str
    facture_id: int
    facture_numero: Optional[str] = None
    client_id: int
    client_username: Optional[str] = None
    montant: float
    date_paiement: datetime
    mode_paiement: str
    reference: Optional[str] = None
    statut: str
    created_at: datetime
    
    @staticmethod
    def resolve_facture_numero(obj) -> Optional[str]:
        return obj.facture.numero if obj.facture else None
    
    @staticmethod
    def resolve_client_username(obj) -> Optional[str]:
        return obj.client.username if obj.client else None


# ==============================================================================
# STATISTIQUES PAR PÉRIODE
# ==============================================================================
class StatsPeriodeSchema(Schema):
    """Statistiques pour une période spécifique."""
    date: str
    montant: float
    nombre_paiements: int
    nombre_concessions: int