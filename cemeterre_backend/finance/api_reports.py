"""
finance/api_reports.py — API pour les rapports et statistiques financières.
Compatible Django Ninja.
"""
from ninja import Router
from ninja_jwt.authentication import JWTAuth
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, date
from typing import Optional

from .models import Facture, Paiement
from .schemas_reports import (
    FinanceDashboardSchema,
    RapportFinancierSchema,
    PaiementOut,
    StatsPeriodeSchema
)
from cemetery.models import Concession
from core.permissions import require_role

router = Router(auth=JWTAuth(), tags=["Finance Reports"])


# ==============================================================================
# DASHBOARD FINANCIER
# ==============================================================================
@router.get("/finance/dashboard/", response=FinanceDashboardSchema)
@require_role("admin", "secretariat")
def get_finance_dashboard(request):
    """Retourne les KPIs financiers pour le dashboard."""
    today = timezone.now().date()
    first_day_month = today.replace(day=1)
    first_day_year = today.replace(month=1, day=1)
    
    # Paiements du jour / mois / année
    paiements_jour = Paiement.objects.filter(
        date_paiement__date=today,
        statut="valide"
    )
    paiements_mois = Paiement.objects.filter(
        date_paiement__date__gte=first_day_month,
        statut="valide"
    )
    paiements_annee = Paiement.objects.filter(
        date_paiement__date__gte=first_day_year,
        statut="valide"
    )
    
    # Chiffre d'affaires
    ca_jour = paiements_jour.aggregate(total=Sum('montant'))['total'] or 0
    ca_mois = paiements_mois.aggregate(total=Sum('montant'))['total'] or 0
    ca_annee = paiements_annee.aggregate(total=Sum('montant'))['total'] or 0
    
    # Factures
    factures_en_attente = Facture.objects.filter(statut="en_attente").count()
    factures_payees = Facture.objects.filter(statut="payee").count()
    factures_annulees = Facture.objects.filter(statut="annulee").count()
    montant_en_attente = Facture.objects.filter(
        statut="en_attente"
    ).aggregate(total=Sum('montant_total'))['total'] or 0
    
    # Concessions
    concessions_mois = Concession.objects.filter(
        created_at__date__gte=first_day_month
    ).count()
    concessions_annee = Concession.objects.filter(
        created_at__date__gte=first_day_year
    ).count()
    
    # Recettes par type de concession
    recettes_temporaire = Concession.objects.filter(
        type_concession="temporaire",
        is_paid=True
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    recettes_trentenaire = Concession.objects.filter(
        type_concession="trentenaire",
        is_paid=True
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    recettes_cinquantenaire = Concession.objects.filter(
        type_concession="cinquantenaire",
        is_paid=True
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    recettes_perpetuelle = Concession.objects.filter(
        type_concession="perpetuelle",
        is_paid=True
    ).aggregate(total=Sum('montant'))['total'] or 0
    
    # Évolution mensuelle (12 derniers mois)
    evolution_mensuelle = []
    for i in range(11, -1, -1):
        mois_date = today - timedelta(days=i * 30)
        mois_debut = mois_date.replace(day=1)
        if mois_debut.month == 12:
            mois_fin = mois_debut.replace(year=mois_debut.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            mois_fin = mois_debut.replace(month=mois_debut.month + 1, day=1) - timedelta(days=1)
        
        montant = Paiement.objects.filter(
            date_paiement__date__gte=mois_debut,
            date_paiement__date__lte=mois_fin,
            statut="valide"
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        evolution_mensuelle.append({
            "month": mois_debut.strftime("%Y-%m"),
            "label": mois_debut.strftime("%b %Y"),
            "amount": float(montant)
        })
    
    return {
        "ca_jour": float(ca_jour),
        "ca_mois": float(ca_mois),
        "ca_annee": float(ca_annee),
        "paiements_jour": paiements_jour.count(),
        "paiements_mois": paiements_mois.count(),
        "paiements_annee": paiements_annee.count(),
        "factures_en_attente": factures_en_attente,
        "factures_payees": factures_payees,
        "factures_annulees": factures_annulees,
        "montant_en_attente": float(montant_en_attente),
        "concessions_creees_mois": concessions_mois,
        "concessions_creees_annee": concessions_annee,
        "recettes_temporaire": float(recettes_temporaire),
        "recettes_trentenaire": float(recettes_trentenaire),
        "recettes_cinquantenaire": float(recettes_cinquantenaire),
        "recettes_perpetuelle": float(recettes_perpetuelle),
        "evolution_mensuelle": evolution_mensuelle
    }


# ==============================================================================
# RAPPORT FINANCIER
# ==============================================================================
@router.get("/finance/rapport/", response=RapportFinancierSchema)
@require_role("admin", "secretariat")
def get_rapport_financier(
    request,
    date_debut: date,
    date_fin: date,
    type_rapport: str = "personnalise"
):
    """Génère un rapport financier pour une période donnée."""
    
    # Paiements de la période
    paiements = Paiement.objects.filter(
        date_paiement__date__gte=date_debut,
        date_paiement__date__lte=date_fin,
        statut="valide"
    ).select_related("facture", "client")
    
    total_montant = paiements.aggregate(total=Sum('montant'))['total'] or 0
    
    # Par mode de paiement
    par_mode = (
        paiements.values("mode_paiement")
        .annotate(total=Sum('montant'), count=Count('id'))
        .order_by("-total")
    )
    
    # Par type de concession
    par_type = (
        Concession.objects.filter(
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin,
            is_paid=True
        )
        .values("type_concession")
        .annotate(total=Sum('montant'), count=Count('id'))
        .order_by("-total")
    )
    
    # Évolution journalière
    evolution_journaliere = []
    current_date = date_debut
    while current_date <= date_fin:
        montant_jour = paiements.filter(
            date_paiement__date=current_date
        ).aggregate(total=Sum('montant'))['total'] or 0
        
        count_jour = paiements.filter(
            date_paiement__date=current_date
        ).count()
        
        evolution_journaliere.append({
            "date": current_date.isoformat(),
            "montant": float(montant_jour),
            "nombre_paiements": count_jour
        })
        current_date += timedelta(days=1)
    
    return {
        "periode_debut": date_debut,
        "periode_fin": date_fin,
        "type_rapport": type_rapport,
        "total_paiements": paiements.count(),
        "total_montant": float(total_montant),
        "total_factures": Facture.objects.filter(
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin
        ).count(),
        "total_concessions": Concession.objects.filter(
            created_at__date__gte=date_debut,
            created_at__date__lte=date_fin
        ).count(),
        "par_mode_paiement": list(par_mode),
        "par_type_concession": list(par_type),
        "evolution_journaliere": evolution_journaliere
    }


# ==============================================================================
# LISTE DES PAIEMENTS
# ==============================================================================
@router.get("/finance/paiements/", response=list[PaiementOut])
@require_role("admin", "secretariat")
def list_paiements(
    request,
    date_debut: Optional[date] = None,
    date_fin: Optional[date] = None,
    mode_paiement: Optional[str] = None,
    search: Optional[str] = None
):
    """Liste tous les paiements avec filtres."""
    queryset = Paiement.objects.all().select_related("facture", "client")
    
    if date_debut:
        queryset = queryset.filter(date_paiement__date__gte=date_debut)
    if date_fin:
        queryset = queryset.filter(date_paiement__date__lte=date_fin)
    if mode_paiement:
        queryset = queryset.filter(mode_paiement=mode_paiement)
    if search:
        queryset = queryset.filter(
            Q(client__username__icontains=search) |
            Q(client__first_name__icontains=search) |
            Q(client__last_name__icontains=search) |
            Q(reference__icontains=search) |
            Q(facture__numero__icontains=search)
        )
    
    return queryset.order_by("-date_paiement")[:100]


# ==============================================================================
# STATISTIQUES PAR MODE DE PAIEMENT
# ==============================================================================
@router.get("/finance/stats-par-mode/")
@require_role("admin", "secretariat")
def stats_par_mode_paiement(request, annee: int = None):
    """Statistiques groupées par mode de paiement pour une année."""
    if not annee:
        annee = timezone.now().year
    
    paiements = Paiement.objects.filter(
        date_paiement__year=annee,
        statut="valide"
    )
    
    stats = (
        paiements.values("mode_paiement")
        .annotate(
            total_montant=Sum('montant'),
            nombre=Count('id')
        )
        .order_by("-total_montant")
    )
    
    return {
        "annee": annee,
        "stats": list(stats)
    }