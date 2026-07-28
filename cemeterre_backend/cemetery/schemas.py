"""
projet_cimetiere/cemeterre_backend/cemetery/schemas.py
Schemas Django Ninja pour le module Cimetière.
CORRECTIONS :
- Ajout de espacement_caveaux dans les schémas Cemetery
- Ajout des nouveaux champs dans les schémas Section
- Ajout des schémas AlleeIn, AlleeOut, CemeteryInitializationSchema
"""

from ninja import Schema
from pydantic import Field, computed_field
from typing import Optional, Any, Literal, List
from datetime import date, datetime
from pydantic import constr, conint, confloat, condecimal


# ==============================================================================
# CEMETERY SCHEMAS
# ==============================================================================
class CemeteryIn(Schema):
    name: str
    city: str
    address: str
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    total_area: confloat(gt=0)
    non_exploitable_area: confloat(ge=0) = 0
    longueur_totale: confloat(gt=0) = 100
    largeur_totale: confloat(gt=0) = 100
    grave_length: confloat(gt=0) = 2.5
    grave_width: confloat(gt=0) = 1.2
    # ✅ NOUVEAU
    espacement_caveaux: confloat(ge=0) = 0.5


class CemeteryUpdate(Schema):
    name: Optional[str] = None
    city: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    total_area: Optional[confloat(gt=0)] = None
    non_exploitable_area: Optional[confloat(ge=0)] = None
    longueur_totale: Optional[confloat(gt=0)] = None
    largeur_totale: Optional[confloat(gt=0)] = None
    grave_length: Optional[confloat(gt=0)] = None
    grave_width: Optional[confloat(gt=0)] = None
    # ✅ NOUVEAU
    espacement_caveaux: Optional[confloat(ge=0)] = None


class CemeteryOut(Schema):
    id: int
    name: str
    city: str
    address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area: float
    non_exploitable_area: float
    longueur_totale: float
    largeur_totale: float
    grave_length: float
    grave_width: float
    espacement_caveaux: float = 0.5  # ✅ NOUVEAU
    calculated_capacity: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    bounds: Optional[dict] = None


# ==============================================================================
# ALLEE SCHEMAS (NOUVEAU)
# ==============================================================================
class AlleeIn(Schema):
    nom: str
    type_allee: Literal['principale', 'secondaire', 'sentier'] = 'secondaire'
    largeur: confloat(gt=0) = 3.0
    coordinates: list  # [[lat1, lon1], [lat2, lon2], ...]


class AlleeOut(Schema):
    id: int
    cemetery_id: int
    nom: str
    type_allee: str
    largeur: float
    coordinates: list
    surface_calculee: Optional[float] = None
    created_at: datetime


# ==============================================================================
# SECTION SCHEMAS
# ==============================================================================
class SectionIn(Schema):
    cemetery_id: int
    name: str
    is_exploitable: bool = True
    description: Optional[str] = ""
    longueur: confloat(gt=0) = 50
    largeur: confloat(gt=0) = 20
    zone_non_exploitable: confloat(ge=0) = 0
    # ✅ NOUVEAUX CHAMPS
    polygon_coords: Optional[list] = None
    ordre: Optional[int] = None


class SectionUpdate(Schema):
    name: Optional[str] = None
    is_exploitable: Optional[bool] = None
    description: Optional[str] = None
    longueur: Optional[confloat(gt=0)] = None
    largeur: Optional[confloat(gt=0)] = None
    zone_non_exploitable: Optional[confloat(ge=0)] = None
    # ✅ NOUVEAUX CHAMPS
    polygon_coords: Optional[list] = None
    ordre: Optional[int] = None


class SectionOut(Schema):
    id: int
    cemetery_id: int
    name: str
    is_exploitable: bool
    description: Optional[str] = None
    longueur: float
    largeur: float
    zone_non_exploitable: float
    # ✅ NOUVEAUX CHAMPS
    polygon_coords: Optional[list] = None
    surface_calculee: Optional[float] = None
    capacite_caveaux: Optional[int] = None
    ordre: int = 0
    created_at: datetime


# ==============================================================================
# GRAVE SCHEMAS
# ==============================================================================
class GraveIn(Schema):
    section_id: int
    code: constr(pattern=r'^[A-Z]-[0-9]{3}$')
    status: Literal['available', 'reserved', 'occupied', 'non_exploitable'] = 'available'
    grave_type: str = "simple"
    length: confloat(gt=0) = 2.5
    width: confloat(gt=0) = 1.2
    capacity: conint(gt=0) = 1
    price: condecimal(gt=0, decimal_places=2)
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    notes: Optional[str] = ""


class GraveUpdate(Schema):
    code: Optional[constr(pattern=r'^[A-Z]-[0-9]{3}$')] = None
    status: Optional[Literal['available', 'reserved', 'occupied', 'non_exploitable']] = None
    grave_type: Optional[str] = None
    length: Optional[confloat(gt=0)] = None
    width: Optional[confloat(gt=0)] = None
    capacity: Optional[conint(gt=0)] = None
    price: Optional[condecimal(gt=0, decimal_places=2)] = None
    latitude: Optional[confloat(ge=-90, le=90)] = None
    longitude: Optional[confloat(ge=-180, le=180)] = None
    notes: Optional[str] = None


class GraveOut(Schema):
    id: int
    section_id: int
    code: str
    status: str
    grave_type: str
    length: float
    width: float
    capacity: int
    price: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    location: Optional[Any] = Field(default=None, exclude=True)

    @computed_field
    @property
    def latitude(self) -> Optional[float]:
        return float(self.location.y) if self.location else None

    @computed_field
    @property
    def longitude(self) -> Optional[float]:
        return float(self.location.x) if self.location else None


class GenerateGridSchema(Schema):
    section_id: int
    rows: conint(gt=0, le=50)
    cols: conint(gt=0, le=50)
    start_lat: confloat(ge=-90, le=90)
    start_lng: confloat(ge=-180, le=180)
    spacing_meters: confloat(gt=0) = 3.0
    prefix: constr(pattern=r'^[A-Z]$') = "A"
    price: condecimal(gt=0, decimal_places=2) = 50000.0


# ==============================================================================
# CONCESSION SCHEMAS (MIS À JOUR)
# ==============================================================================
class ConcessionIn(Schema):
    """Schéma pour création manuelle (admin)"""
    grave_id: int
    user_id: int
    type_concession: Literal['temporaire', 'trentenaire', 'cinquantenaire', 'perpetuelle'] = 'temporaire'
    montant: condecimal(gt=0, decimal_places=2)
    date_debut: date
    duree_annees: Optional[conint(gt=0)] = None  # Uniquement pour temporaire
    date_fin: Optional[date] = None  # Calculé automatiquement si non fourni


class ConcessionCreateFromReservationIn(Schema):
    """Schéma pour création depuis une réservation validée"""
    reservation_id: int
    type_concession: Literal['temporaire', 'trentenaire', 'cinquantenaire', 'perpetuelle']
    duree_annees: Optional[conint(gt=0)] = None  # Uniquement pour temporaire
    observations: Optional[str] = ""


class ConcessionRenewalIn(Schema):
    """Schéma pour renouvellement"""
    type_concession: Literal['temporaire', 'trentenaire', 'cinquantenaire'] = 'temporaire'
    duree_annees: conint(gt=0)
    montant: Optional[condecimal(gt=0, decimal_places=2)] = None  # Si non fourni, utilise l'ancien montant


class ConcessionOut(Schema):
    id: int
    grave_id: int
    user_id: int
    type_concession: str
    montant: float
    date_debut: date
    duree_annees: Optional[int] = None
    date_fin: Optional[date] = None
    is_paid: bool
    status: str
    renewed_count: int = 0
    last_renewal_at: Optional[datetime] = None
    created_at: datetime
    
    # Champs enrichis
    grave_code: Optional[str] = None
    section_name: Optional[str] = None
    client_username: Optional[str] = None
    client_email: Optional[str] = None
    days_remaining: Optional[int] = None
    is_expiring_soon: bool = False
    is_expired: bool = False
    is_perpetuelle: bool = False

    @staticmethod
    def resolve_grave_code(obj) -> Optional[str]:
        return obj.grave.code if obj.grave else None

    @staticmethod
    def resolve_section_name(obj) -> Optional[str]:
        if obj.grave and obj.grave.section:
            return obj.grave.section.name
        return None

    @staticmethod
    def resolve_client_username(obj) -> Optional[str]:
        return obj.user.username if obj.user else None

    @staticmethod
    def resolve_client_email(obj) -> Optional[str]:
        return obj.user.email if obj.user else None

    @staticmethod
    def resolve_days_remaining(obj) -> Optional[int]:
        return obj.days_remaining

    @staticmethod
    def resolve_is_expiring_soon(obj) -> bool:
        return obj.is_expiring_soon

    @staticmethod
    def resolve_is_expired(obj) -> bool:
        return obj.is_expired

    @staticmethod
    def resolve_is_perpetuelle(obj) -> bool:
        return obj.type_concession == 'perpetuelle'


class ConcessionRenewalOut(Schema):
    id: int
    concession_id: int
    ancienne_date_fin: date
    nouvelle_date_fin: date
    duree_extension_annees: int
    montant_paye: float
    facture_id: Optional[int] = None
    renewed_by: Optional[str] = None
    date_renouvellement: datetime
    observations: Optional[str] = None

    @staticmethod
    def resolve_renewed_by(obj) -> Optional[str]:
        return obj.renewed_by.username if obj.renewed_by else None


# ==============================================================================
# INHUMATION SCHEMAS
# ==============================================================================
class InhumationIn(Schema):
    grave_id: int
    concession_id: Optional[int] = None
    reservation_id: Optional[int] = None
    defunt_prenom: str
    defunt_nom: str
    defunt_date_naissance: Optional[date] = None
    defunt_date_deces: date
    agent_inhumation_id: Optional[int] = None
    observations: Optional[str] = ""
    heure_inhumation: Optional[str] = None


class InhumationOut(Schema):
    id: int
    grave_id: int
    grave_code: Optional[str] = None
    concession_id: Optional[int] = None
    reservation_id: Optional[int] = None
    defunt_prenom: str
    defunt_nom: str
    defunt_date_naissance: Optional[date] = None
    defunt_date_deces: date
    date_inhumation: datetime
    agent_inhumation_id: Optional[int] = None
    agent_username: Optional[str] = None
    observations: Optional[str] = None
    created_at: datetime
    heure_inhumation: Optional[str] = None

    @staticmethod
    def resolve_grave_code(obj) -> Optional[str]:
        return obj.grave.code if obj.grave else None

    @staticmethod
    def resolve_agent_username(obj) -> Optional[str]:
        return obj.agent_inhumation.username if obj.agent_inhumation else None

    @staticmethod
    def resolve_heure_inhumation(obj) -> Optional[str]:
        if obj.date_inhumation:
            return obj.date_inhumation.strftime("%H:%M")
        return None


# ==============================================================================
# EXHUMATION SCHEMAS
# ==============================================================================
class ExhumationIn(Schema):
    inhumation_id: int
    demandeur_id: Optional[int] = None
    motif: str
    date_prevue: date


class ExhumationStatusSchema(Schema):
    status: str
    motif_rejet: Optional[str] = None
    date_exhumation: Optional[date] = None
    observations: Optional[str] = None


class ExhumationOut(Schema):
    id: int
    inhumation_id: Optional[int] = None
    grave_id: int
    grave_code: Optional[str] = None
    defunt_nom: Optional[str] = None
    defunt_prenom: Optional[str] = None
    demandeur_id: int
    demandeur_username: Optional[str] = None
    motif: str
    date_prevue: date
    date_exhumation: Optional[date] = None
    motif_rejet: Optional[str] = None
    status: str
    observations: Optional[str] = None
    created_at: datetime

    @staticmethod
    def resolve_grave_code(obj) -> Optional[str]:
        return obj.grave.code if obj.grave else (obj.inhumation.grave.code if obj.inhumation and obj.inhumation.grave else None)

    @staticmethod
    def resolve_defunt_nom(obj) -> Optional[str]:
        return obj.inhumation.defunt_nom if obj.inhumation else None

    @staticmethod
    def resolve_defunt_prenom(obj) -> Optional[str]:
        return obj.inhumation.defunt_prenom if obj.inhumation else None

    @staticmethod
    def resolve_demandeur_username(obj) -> Optional[str]:
        return obj.demandeur.username if obj.demandeur else None


class RejectExhumationIn(Schema):
    """Schéma pour le rejet d'une exhumation"""
    motif_rejet: str


class CompleteExhumationIn(Schema):
    """Schéma pour la clôture d'une exhumation"""
    date_exhumation: str
    observations: Optional[str] = ""


# ==============================================================================
# SCHÉMA D'INITIALISATION COMPLÈTE (NOUVEAU)
# ==============================================================================
class CemeteryInitializationSchema(Schema):
    """Schéma pour l'initialisation complète du cimetière avec allées et sections."""
    cemetery: CemeteryIn
    allees: List[AlleeIn] = []
    # Les sections seront générées automatiquement, mais on peut fournir des noms personnalisés
    section_names: Optional[List[str]] = None


# ==============================================================================
# STATS & AUDIT SCHEMAS
# ==============================================================================
class ConcessionStatsSchema(Schema):
    total: int
    actives: int
    expired: int
    resiliees: int
    temporaires: int
    perpetuelles: int
    expiring_in_15_days: int
    revenus_total: float
    taux_renouvellement: float


class AuditLogOut(Schema):
    id: int
    user_id: Optional[int] = None
    action: str
    model_name: str
    object_id: Optional[int] = None
    details: Optional[str] = None
    timestamp: datetime

# ==============================================================================
# SCHEMAS POUR SIGNALEMENT DE CAVEAUX (NOUVEAU)
# ==============================================================================
class SignalerProblemeSchema(Schema):
    """Schéma pour signaler un problème sur un caveau (Agent)"""
    motif: str
    description: Optional[str] = ""
    photos: Optional[list] = None


class ValiderSignalementSchema(Schema):
    """Schéma pour valider un signalement (Admin)"""
    pass


class RejeterSignalementSchema(Schema):
    """Schéma pour rejeter un signalement (Admin)"""
    motif_rejet: str


class CaveauSignalementSchema(Schema):
    """Schéma de sortie pour un signalement"""
    id: int
    grave_id: int
    grave_code: Optional[str] = None
    motif: str
    description: Optional[str] = None
    statut: str
    signale_par: Optional[str] = None
    valide_par: Optional[str] = None
    motif_rejet: Optional[str] = None
    date_signalement: datetime
    date_validation: Optional[datetime] = None
    photos: Optional[list] = None

    @staticmethod
    def resolve_grave_code(obj) -> Optional[str]:
        return obj.grave.code if obj.grave else None

    @staticmethod
    def resolve_signale_par(obj) -> Optional[str]:
        return obj.signale_par.username if obj.signale_par else None

    @staticmethod
    def resolve_valide_par(obj) -> Optional[str]:
        return obj.valide_par.username if obj.valide_par else None