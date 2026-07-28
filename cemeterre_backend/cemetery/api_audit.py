"""
cemetery/api_audit.py — Endpoint pour le journal d'audit.
Compatible avec le modèle AuditLog et le décorateur require_role.
"""
from ninja import Router, Query
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from .models import AuditLog
from core.permissions import require_role

router = Router(tags=["Audit"])


@router.get("/logs")
@require_role("admin", "secretariat")
def get_audit_logs(request, 
                   search: str = Query(None), 
                   days: int = Query(30), 
                   action: str = Query(None), 
                   model_name: str = Query(None)):
    """
    Récupère les logs avec filtres, triés du plus récent au plus ancien.
    Limite à 100 derniers pour la performance.
    """
    qs = AuditLog.objects.select_related("user").all().order_by("-timestamp")
    
    # Filtre par période
    if days:
        qs = qs.filter(timestamp__gte=timezone.now() - timedelta(days=int(days)))
    
    # Filtre par type d'action
    if action:
        qs = qs.filter(action=action)
    
    # Filtre par module (model_name)
    if model_name:
        qs = qs.filter(model_name__icontains=model_name)
    
    # Recherche textuelle (utilisateur, détails)
    if search:
        qs = qs.filter(
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(details__icontains=search)
        )
        
    # Limite à 100 derniers logs
    logs = qs[:100]
    
    return {
        "results": [
            {
                "id": log.id,
                "timestamp": log.timestamp.isoformat(),
                "user": f"{log.user.first_name} {log.user.last_name}".strip() or log.user.username if log.user else "Système",
                "action": log.action,
                "model_name": log.model_name,
                "details": log.details,
            }
            for log in logs
        ]
    }